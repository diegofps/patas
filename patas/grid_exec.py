from .utils import expand_path, error, warn, info, debug, critical, abort, readlines, clean_folder, estimate, human_time, quote, colors
from .schemas import Experiment, Cluster, Node, format_as_dict

from multiprocessing import Process, Queue
from subprocess import Popen, PIPE
from datetime import datetime

import hashlib
import base64
import select
import shlex
import copy
import time
import yaml
import pty
import sys
import os


KEY_SSH_ON  = b'74ffc7c4-a6ad-4315-94cb-59d045a230c0'
KEY_SSH_OFF = b'93dfc971-fa64-4beb-a24e-d8874738b9ca'
KEY_CMD_ON  = b'15e6896c-3ea7-42a0-aa32-23e2ab3c0e12'
KEY_CMD_OFF = b'e04a4348-8092-46a6-8e0c-d30d10c86fb3'

echo = lambda x: b" echo -e \"%s\"" % x.replace(b"-", b"-\b-")

ECHO_SSH_ON  = echo(KEY_SSH_ON)
ECHO_SSH_OFF = echo(KEY_SSH_OFF)
ECHO_CMD_ON  = echo(KEY_CMD_ON)
ECHO_CMD_OFF = b" echo -en \"\n $? %s\"" % KEY_CMD_OFF.replace(b"-", b"-\b-")


def combine_variables(variables, combination={}):

    if len(variables) == len(combination):
        yield copy.copy(combination)
    
    else:
        var = variables[len(combination)]
        name = var.name
        
        for value in var.values:
            combination[name] = value
            
            for tmp in combine_variables(variables, combination):
                yield tmp
            
        del combination[name]


class QueueMsg(dict):

    def __init__(self, action, source=-1):
        self.action = action
        self.source = source
        self.data = {}
    
    def __setstate__(self, state):
        self.__dict__ = state

    def __getstate__(self):
        return self.__dict__

    def __getattr__(self, key):
        return self[key]
    
    def __setattr__(self, key, value):
        self[key] = value


class Task:

    def __init__(self, 
            experiment_name, task_output_dir, work_dir, experiment_idd, combination_idd, 
            repeat_idd, task_idd, combination, cmdlines, max_tries):

        self.experiment_name = experiment_name
        self.combination_idd = combination_idd
        self.experiment_idd = experiment_idd
        self.output_dir = task_output_dir
        self.combination = combination
        self.repeat_idd = repeat_idd
        self.max_tries = max_tries
        self.work_dir = work_dir
        self.task_idd = task_idd
        self.commands = cmdlines
        self.assigned_to = None
        self.started_at = None
        self.ended_at = None
        self.duration = None
        self.success = None
        self.output = None
        self.status = None
        self.tries = 0
    
    
    def __repr__(self):
        comb = ";".join(f"{k}={v}" for k, v in self.combination.items())
        return "%d %d %d %d %s %s" % (self.experiment_idd, self.combination_idd, 
                    self.repeat_idd, self.task_idd, comb, self.commands)


class ExecutorBuilder:

    def __init__(self, executor_type, node):
        self.executor_type = executor_type
        self.node = node

    def __call__(self):
        return self.executor_type(self.node)


class BashExecutor:
    
    def __init__(self, node):

        self.is_alive = True
        self.node = node
    
    def execute(self, initrc, cmds):

        if type(cmds) is not list:
            cmds = [cmds]

        cmds = [x + b' 2>&1 ' for x in cmds]

        p1 = b" ; ".join(initrc)
        p3 = b" ; ".join(cmds)

        cmd_str = b" %s ; %s " % (p1, p3)
        cmd_str = "bash -c " + quote(cmd_str.decode('utf-8'))
        
        ps = Popen(shlex.split(cmd_str), stdout=PIPE)

        status = ps.wait()
        stdout = ps.stdout

        return (status == 0), stdout, status


class SSHExecutor:

    def __init__(self, node):

        self.node = node
        self.is_alive = False

        # Opens a pseudo-terminal
        self.master, self.slave = pty.openpty()
        self._start_bash()
        
        self.conn_string = self._build_connnection_string(self.node)

        self._connect()
    
    def _build_connnection_string(self, node):

        tokens = [b' ssh']

        if node.private_key:
            tokens.append(b' -i ')
            tokens.append(node.private_key.encode())
        
        if node.port:
            tokens.append(b' -p ')
            tokens.append(str(node.port).encode())

        tokens.append(b' -t ')
        tokens.append(node.credential.encode())

        tokens.append(b" '")
        tokens.append(ECHO_SSH_ON)
        tokens.append(b" ; bash' ; ")
        tokens.append(ECHO_SSH_OFF)
        tokens.append(b'\n')
        
        return b"".join(tokens)


    def _start_bash(self):

        debug("Starting bash")

        self.popen = Popen(
                shlex.shlex("bash"),
                preexec_fn=os.setsid,
                stdin=self.slave,
                stdout=self.slave,
                stderr=self.slave,
                universal_newlines=True)


    def _connect(self):

        conn_try = 1

        while True:
            debug("Connection attempt:", conn_try)

            os.write(self.master, self.conn_string)
            found_ssh_off = False
            found_ssh_on = False
            lines = []

            while True:
                if self.popen.poll() is not None:
                    warn("Bash has died, starting it again")
                    self._start_bash()
                
                r, _, _ = select.select([self.master], [], [])

                if not self.master in r:
                    warn("Unexpected file descriptor while stablishing connection")
                    continue
                
                for i in range(*readlines(self.master, lines, verbose=False)):
                    line = lines[i]

                    if KEY_SSH_ON in line:
                        found_ssh_on = True
                    
                    elif KEY_SSH_OFF in line:
                        found_ssh_off = True
                
                if found_ssh_on:
                    debug("SSH connection established")
                    self.is_alive = True
                    return
                
                if found_ssh_off:
                    warn("SSH connection against %s has failed, trying again" % self.node.name)
                    break

            warn("Sleeping before next try...")
            time.sleep(1)
            conn_try += 1


    def execute(self, initrc, cmds):

        if type(cmds) is not list:
            cmds = [cmds]

        lines = []
        output_start = 0
        output_end = None

        p1 = b" ; ".join(initrc)
        p2 = ECHO_CMD_ON
        p3 = b" ; ".join(cmds)
        p4 = ECHO_CMD_OFF

        cmd_str = b" %s ; %s ; %s ; %s\n" % (p1, p2, p3, p4)

        os.write(self.master, cmd_str)
        
        while True:
            if self.popen.poll() is not None:
                return False, None, None
            
            r, _, _ = select.select([self.master], [], [])

            if not self.master in r:
                warn("Unexpected file descriptor while searching for command output")
                continue

            for i in range(*readlines(self.master, lines, verbose=False)):
                line = lines[i]

                if KEY_SSH_OFF in line:
                    warn("Found KEY_SSH_OFF")
                    self.popen.kill()
                    self.is_alive = False
                    return False, None, None
                
                elif KEY_CMD_ON in line:
                    #debug("Found KEY_CMD_ON")
                    output_start = i + 1
                
                elif KEY_CMD_OFF in line and output_end is None:
                    #debug("Found KEY_CMD_OFF")
                    output_end = i
            
            if output_end is not None:
                status = lines[output_end].strip().split()[0].decode("utf-8") if output_end < len(lines) else "255"
                break

        return (status == "0"), lines[output_start:output_end], status


class WorkerProcess:

    def __init__(self, worker_idd, executor_builder, env_variables):

        self.executor_builder = executor_builder
        self.env_variables = env_variables
        self.worker_idd = worker_idd
        self.process = None
        self.queue = None


    def start(self, queue_master):

        self.queue = Queue()
        self.process = Process(target=self.run, args=(self.queue, queue_master))
        self.process.start()


    # def debug(self, *args):
    #     debug(self.worker_idd, "|", *args)


    def run(self, queue_in, queue_master):

        try:
            executor = self.executor_builder()

            msg_out = QueueMsg("ready", self.worker_idd)
            queue_master.put(msg_out)
            
            while True:
                msg_in = queue_in.get()

                if msg_in.action == "execute":
                    success = self.execute(msg_in, executor)

                    msg_out = QueueMsg("finished", self.worker_idd)
                    msg_out.success = success
                    queue_master.put(msg_out)

                    if not executor.is_alive:
                        executor = self.executor_builder()

                    msg_out = QueueMsg("ready", self.worker_idd)
                    queue_master.put(msg_out)
                
                elif msg_in.action == "terminate":
                    break
                
                else:
                    warn("Unknown action:", msg_in.action)
            
            msg_out = QueueMsg("ended", self.worker_idd)
            queue_master.put(msg_out)
        except KeyboardInterrupt:
            pass


    def execute(self, msg_in, executor):

        task:Task = msg_in.task

        # Prepare the initrc

        env_variables = copy.copy(self.env_variables)
        env_variables["PATAS_WORK_DIR"] = task.work_dir

        for k,v in task.combination.items():
            env_variables["PATAS_VAR_" + k] = str(v)

        initrc = [b"export %s=\"%s\"" % (a.encode(), b.encode()) for a, b in env_variables.items()]
        initrc.insert(0, b"cd \"%s\"" % task.work_dir.encode())

        # Prepare the command line we will execute

        cmdline = " ; ".join(task.commands).encode()

        # Execute this task

        task.started_at = datetime.now()
        task.success, task.output, task.status = executor.execute(initrc, cmdline)
        task.ended_at = datetime.now()
        task.duration = (task.ended_at - task.started_at).total_seconds()

        # Create the task folder and clean any old .done file

        done_filepath = os.path.join(task.output_dir, ".done")
        os.makedirs(task.output_dir, exist_ok=True)
        if os.path.exists(done_filepath):
            os.remove(done_filepath)

        # Dump task info
        
        info = {
            "task_id": task.task_idd,
            "repeat_id": task.repeat_idd,
            "experiment_id": task.experiment_idd,
            "experiment_name": task.experiment_name,
            "combination_id": task.combination_idd,
            "combination": task.combination,
            "started_at": task.started_at,
            "ended_at": task.ended_at,
            "duration": task.duration,
            "env_variables": env_variables,
            "max_tries": task.max_tries,
            "tries": task.tries + 1,
            "output_dir": task.output_dir,
            "work_dir": task.work_dir,
            "commands": task.commands,
            "assigned_to": task.assigned_to,
        }

        filepath = os.path.join(task.output_dir, "info.yml")
        with open(filepath, "w") as fout:
            yaml.dump(info, fout, default_flow_style=False)
        
        # Dump task output

        filepath = os.path.join(task.output_dir, "stdout")
        with open(filepath, "wb") as fout:
            fout.writelines(task.output)

        # Create .done file if the task succeded

        if task.success:
            with open(done_filepath, 'a'):
                os.utime(done_filepath, None)

        # Write output to stdout if the task failed

        else:
            warn("--- TASK %d FAILED WITH EXIT CODE %s ---" % (task.task_idd, task.status))
            for line in task.output:
                os.write(sys.stdout.fileno(), line)
            warn("--- END OF FAILED OUTPUT ---")

        return task.success


class GridExec():

    def __init__(self, task_filters, node_filters, 
            output_dir, redo_tasks, recreate, confirmed,
            experiments, clusters):

        self.output_folder = expand_path(output_dir)
        self.task_filters = task_filters
        self.node_filters = node_filters
        self.experiments = experiments
        self.redo_tasks = redo_tasks
        self.confirmed = confirmed
        self.recreate = recreate
        self.clusters = clusters
        self.workers:list[WorkerProcess] = None
        self.tasks:list[Task] = None


    def start(self):

        os.makedirs(self.output_folder, exist_ok=True)

        self._show_summary(self.experiments, self.clusters, self.confirmed)
        self._write_signature()
        self.tasks   = self._create_tasks(self.experiments, self.output_folder, self.redo_tasks, self.task_filters)
        self.workers = self._create_workers(self.clusters, self.node_filters)
        self._exec()


    def _show_summary(self, experiments, clusters, confirmed):

        # Display experiments

        print(colors.white("\n --- Experiments --- \n"))

        total_tasks = 0
        experiment: Experiment

        for experiment in experiments:
            variables = experiment.vars
            current = 1

            for var in variables:
                current *= len(var.values)
            
            current *= experiment.repeat
            total_tasks += current

            print(f"'{experiment.name}' has {len(variables)} variable(s) and produces {current} task(s):")
            for var in variables:
                print(f"    {var.name} = {str(var.values)}, len = {len(var.values)}")
        
        # Display clusters

        print(colors.white("\n --- Clusters --- \n"))

        total_nodes = 0
        total_workers = 0
        node:Node = None
        cluster:Cluster = None

        for cluster in clusters:
            total_nodes += len(cluster.nodes)
            print(f"'{cluster.name}' has {len(cluster.nodes)} node(s):")

            for node in cluster.nodes:
                total_workers += node.workers
                print(f"    '{node.name}' has {node.workers} worker(s)")
        
        # Display total numbers and estimations

        print(colors.white("\n --- Overview --- \n"))

        print(f"Redo:          {self.redo_tasks}")
        print(f"Task filters:  {self.task_filters}")
        print(f"Node filters:  {self.node_filters}")
        print(f"Output folder: {self.output_folder}")
        print(f"Recreate:      {self.recreate}")

        print()

        print(f"Total number of clusters: {len(clusters)}")
        print(f"Total number of nodes:    {total_nodes}")
        print(f"Total number of workers:  {total_workers}")
        print(f"Total number of tasks:    {total_tasks}")

        print()

        print('Estimated time to complete if each task takes:')
        print(f"    One second: { estimate(total_tasks, total_workers,        1) }")
        print(f"    One minute: { estimate(total_tasks, total_workers,       60) }")
        print(f"    One hour:   { estimate(total_tasks, total_workers,    60*60) }")
        print(f"    One day:    { estimate(total_tasks, total_workers, 60*60*24) }")

        print()

        # Confirm

        if not confirmed:
            try:
                while True:
                    option = input('Do you want to continue? [Y/n] ').strip()
                    if option in ['Y', 'y', '']:
                        break
                    elif option in ['N', 'n']:
                        sys.exit(0)
                    else:
                        print('Invalid option')
            except KeyboardInterrupt:
                sys.exit(0)

    def _write_signature(self):

        # Calculate the signature for the received configuration

        key = hashlib.md5()

        key.update(str(format_as_dict(self.experiments)).encode())

        signature = base64.b64encode(key.digest()).decode("utf-8")

        # Data to be saved into the signature file

        info = {
            "output_folder": self.output_folder,
            "task_filters": self.task_filters,
            "node_filters": self.node_filters,
            "experiments": format_as_dict(self.experiments),
            "redo_tasks": self.redo_tasks,
            "recreate": self.recreate,
            "clusters": format_as_dict(self.clusters),
            "signature": signature
        }

        # Load the previous signature file, if it exists

        info_filepath = os.path.join(self.output_folder, "info.yml")

        try:
            with open(info_filepath, "r") as fin:
                other = yaml.load(fin, Loader=yaml.FullLoader)
        except:
            other = None

        # If the previous file was loaded and it has a signature, compare it to the current signature

        if other and "signature" in other and other["signature"] != signature:
            if self.recreate:
                print("Recreating output folder...")
                clean_folder(self.output_folder)
            else:
                abort("The output folder contains a different output configuration. Provide an empty folder or add the parameter --recreate to overwrite this one")

        # Write the new signature file
            
        with open(info_filepath, "w") as fout:
            yaml.dump(info, fout, default_flow_style=False)


    def _create_tasks(self, experiments, output_folder, redo_tasks, task_filters):

        print("Creating tasks...")

        e:Experiment = None
        combination_idd = -1
        experiment_idd = -1
        task_idd = -1
        tasks = []

        for e in experiments:

            experiment_idd += 1

            experiment_filepath = os.path.join(output_folder, e.name)
            info_filepath = os.path.join(experiment_filepath, "info.yml")
            os.makedirs(experiment_filepath, exist_ok=True)

            info = {
                "experiment_name": e.name,
                "workdir": e.workdir,
                "commands": e.cmd,
                "repeat": e.repeat,
                "max_tries": e.max_tries,
                "variables": {v.name:v.values for v in e.vars}
            }

            with open(info_filepath, "w") as fout:
                yaml.dump(info, fout, default_flow_style=False)

            for combination in combine_variables(e.vars):
                combination_idd += 1

                for repeat_idd in range(e.repeat):
                    task_idd += 1

                    if task_filters and not any(a <= task_idd < b for a, b in task_filters):
                        continue

                    task_output_folder = os.path.join(experiment_filepath, str(task_idd))

                    if not redo_tasks and os.path.exists(os.path.join(task_output_folder, ".done")):
                        continue

                    cmds = [x.format(**combination) for x in e.cmd]

                    task = Task(e.name, task_output_folder, e.workdir, experiment_idd, combination_idd, repeat_idd, task_idd, combination, cmds, e.max_tries)
                    tasks.append(task)

        if not tasks:
            abort("No tasks to do.")
        
        return tasks


    def _create_workers(self, clusters, node_filters):

        print("Creating workers...")

        cluster_idd = -1
        worker_idd = -1
        node_idd = -1

        workers = []

        cluster:Cluster = None
        node:Node = None

        for cluster in clusters:
            cluster_idd += 1

            for node in cluster.nodes:
                node_idd += 1

                for _ in range(node.workers):
                    worker_idd += 1

                    if node_filters and not any(all(tag in node.tags for tag in filter) for filter in node_filters):
                        continue

                    if node.hostname in ['localhost', '127.0.0.1']:
                        builder = ExecutorBuilder(BashExecutor, node)    
                    else:
                        builder = ExecutorBuilder(SSHExecutor, node)

                    env_variables = {
                        "PATAS_CLUSTER_NAME": cluster.name,
                        "PATAS_NODE_NAME": node.name,

                        "PATAS_CLUSTER_ID": str(cluster_idd),
                        "PATAS_NODE_ID": str(node_idd),
                        "PATAS_WORKER_ID": str(worker_idd)
                    }

                    worker = WorkerProcess(worker_idd, builder, env_variables)
                    workers.append(worker)
        
        if not workers:
            abort("No workers to work.")
        
        return workers


    def _exec(self):

        self.queue    = Queue()

        self.todo     = copy.copy(self.tasks)
        self.doing    = []
        self.done     = []
        self.given_up = []

        self.idle     = []
        self.ended    = []

        len_todo      = len(str(len(self.todo)))
        len_workers   = len(str(len(self.workers)))
        
        # Start workers

        print()
        info("Starting %d worker(s)" % len(self.workers))

        for worker in self.workers:
            worker.start(self.queue)
        
        info("Worker(s) started")

        # Main loop

        main_loop_started_at = datetime.now()

        try:

            print()
            info("Starting main loop")

            while self.todo or self.doing:

                msg_in = self.queue.get()

                l1 = str(len(self.todo    ))
                l2 = str(len(self.doing   ))
                l3 = str(len(self.done    ))
                l4 = str(len(self.given_up))

                d  = colors.gray("|%s|" % str(datetime.now()))
                l1 = colors.white(" " * (len_todo    - len(l1)) + l1 + " |")
                l2 = colors.white(" " * (len_workers - len(l2)) + l2 + " |")
                l3 = colors.green(" " * (len_todo    - len(l3)) + l3 + " |")
                l4 = colors.red  (" " * (len_todo    - len(l4)) + l4 + " |")

                print(f"{d} {l1} {l2} {l3} {l4}")

                if msg_in.action == "ready":
                    self._ready(msg_in)
                
                elif msg_in.action == "finished":
                    self._finished(msg_in)
                
                else:
                    warn("Unknown action:", msg_in.action)
            
            info("Main loop completed")

        except KeyboardInterrupt:

            print("Operation interrupted")
            return

        main_loop_ended_at = datetime.now()
        main_loop_duration = (main_loop_ended_at - main_loop_started_at).total_seconds()
        
        # Terminate workers

        terminate_loop_started_at = datetime.now()

        try:
            print()
            info("Releasing workers...")

            # Sending TERMINATE signal

            for worker in self.workers:
                msg = QueueMsg("terminate")
                worker.queue.put(msg)
            
            # Waiting for ENDED signal

            while len(self.workers) != len(self.ended):

                msg = self.queue.get()

                if msg.action == "ended":

                    self.ended.append(msg.source)

                    d = colors.gray("|%s|" % str(datetime.now()))

                    l1 = str(len(self.ended))
                    l2 = str(len(self.workers))

                    l1 = " " * (len_workers - len(l1)) + l1
                    l2 = " " * (len_workers - len(l2)) + l2

                    print("%s %sEnded %s / %s%s" % (d, colors.WHITE, l1, l2, colors.RESET))
                
                else:
                    #debug("Ignoring action %s from %s, execution is ending" % (msg.source, msg.action))
                    pass

            info("All workers are resting.")
            
        except KeyboardInterrupt:

            print("Operation interrupted")
            return

        terminate_loop_ended_at = datetime.now()
        terminate_loop_duration = (terminate_loop_ended_at - terminate_loop_started_at).total_seconds()
        
        # Display execution summary

        print(colors.white("\n --- Execution Summary --- \n"))
        print(f"    Time to execute tasks: {human_time(main_loop_duration)}")
        print(f"    Time to terminate workers: {human_time(terminate_loop_duration)}")
        print(f"    Tasks requested: {len(self.tasks)}")
        print(f"    Tasks completed: {len(self.done)}")
        print(f"    Tasks given up: {len(self.given_up)}")
        print()

    def _ready(self, msg_in):

        if self.todo:
            msg_out = QueueMsg("execute")
            msg_out.task = self.todo.pop()
            msg_out.task.assigned_to = msg_in.source

            self.doing.append(msg_out.task)
            self.workers[msg_in.source].queue.put(msg_out)
        
        else:
            self.idle.append(msg_in.source)


    def _finished(self, msg_in):

        for i, x in enumerate(self.doing):
            if x.assigned_to == msg_in.source:
                break
        
        if i == len(self.doing):
            warn("Received finished msg but the task was not found inside the doing list")
            return
        
        task:Task = self.doing[i]
        del self.doing[i]
        task.tries += 1

        if msg_in.success:
            self.done.append(task)
            return

        if task.tries >= task.max_tries:
            critical(f"Giving up on task {task.task_idd}, max_tries reached.")
            self.given_up.append(task)
            return
        
        if not self.idle:
            self.todo.append(task)
            return

        target = self.idle.pop()

        msg_out = QueueMsg("execute")
        msg_out.task = task
        msg_out.task.assigned_to = target

        self.workers[target].queue.put(msg_out)
