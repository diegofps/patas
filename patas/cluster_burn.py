from .utils import expand_path, error, warn, info, debug, critical, readlines, clean_folder, colors
from .schemas import Experiment, Cluster, Node

from multiprocessing import Process, Queue
from datetime import datetime
from subprocess import Popen

import hashlib
import base64
import select
import shlex
import uuid
import copy
import time
import yaml
import pty
import sys
import os

# Print a signature after entering ssh and after disconnecting
# ssh -t wup@172.17.0.3 "echo 12345 ; bash" ; echo '54321'

# Print output code of last command
# echo $?

KEY_SSH_ON = b'74ffc7c4-a6ad-4315-94cb-59d045a230c0'
KEY_SSH_OFF = b'93dfc971-fa64-4beb-a24e-d8874738b9ca'
KEY_CMD_ON = b'15e6896c-3ea7-42a0-aa32-23e2ab3c0e12'
KEY_CMD_OFF = b'e04a4348-8092-46a6-8e0c-d30d10c86fb3'
KEY_OUTPUT_CODE = b'2a25b3bf-efd5-4d38-81dd-1065c683ec85'

echo = lambda x: b" echo -e \"%s\"" % x.replace(b"-", b"-\b-")

ECHO_SSH_ON = echo(KEY_SSH_ON)
ECHO_SSH_OFF = echo(KEY_SSH_OFF)
ECHO_CMD_ON = echo(KEY_CMD_ON)
ECHO_CMD_OFF = b" echo -en \"\n $? %s\"" % KEY_CMD_OFF.replace(b"-", b"-\b-")


def combine_variables(variables, combination=[]):

    if len(variables) == len(combination):
        yield copy.copy(combination)
    
    else:
        var = variables[len(combination)]
        name = var.name
        
        for value in var.values:
            combination.append({"n": name, "v": value})

            for tmp in combine_variables(variables, combination):
                yield tmp
            
            combination.pop()


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
            experiment_name, task_output_dir, work_dir, experiment_idd, perm_idd, 
            repeat_idd, task_idd, combination, cmdlines):

        self.experiment_name = experiment_name
        self.experiment_idd = experiment_idd
        self.output_dir = task_output_dir
        self.combination = combination
        self.repeat_idd = repeat_idd
        self.work_dir = work_dir
        self.perm_idd = perm_idd
        self.task_idd = task_idd
        self.cmdlines = cmdlines
        self.assigned_to = None
        self.started_at = None
        self.ended_at = None
        self.duration = None
        self.success = None
        self.output = None
        self.status = None
        self.tries = 0
    
    
    def __repr__(self):
        comb = ";".join(str(k) + "=" + str(v) for k, v in self.combination.items())
        return "%d %d %d %d %s %s" % (self.experiment_idd, self.perm_idd, 
                    self.repeat_idd, self.task_idd, comb, self.cmdlines)


class ExecutorBuilder:

    def __init__(self, connector, machine):
        self.connector = connector
        self.machine = machine

    def __call__(self):
        return self.connector(self.machine)


class BashExecutor:
    pass


class SSHExecutor:

    def __init__(self, node):

        #self.ssh = BasicSSH(machine.user, machine.ip, machine.ip)
        self.node = node
        self.is_alive = False

        # Opens a pseudo-terminal
        self.master, self.slave = pty.openpty()
        self._start_bash()
        
        self.conn_string = self._build_conn_string(self.node)

        self._connect()
    
    def _build_connnection_string(self, node):

        str = [' ssh']

        if node.private_key:
            str.append(' -i ')
            str.append(node.private_key)
        
        if node.port:
            str.append(' -p ')
            str.append(node.port)

        str.append(' -t ')
        str.append(node.credential)

        str.append(" '")
        str.append(ECHO_SSH_ON)
        str.append(" ; bash' ; ")
        str.append(ECHO_SSH_OFF)
        str.append('\n')
        
        return "".join(str).encode()


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

    def __init__(self, worker_idd, connection_builder, env_variables):

        self.connection_builder = connection_builder
        self.env_variables = env_variables
        self.worker_idd = worker_idd
        self.process = None
        self.queue = None


    def start(self, queue_master):
        self.queue = Queue()
        self.process = Process(target=self.run, args=(self.queue, queue_master))
        self.process.start()


    def debug(self, *args):
        debug(self.worker_idd, "|", *args)


    def run(self, queue_in, queue_master):
        try:
            conn = self.connection_builder()

            msg_out = QueueMsg("ready", self.worker_idd)
            queue_master.put(msg_out)
            
            while True:
                msg_in = queue_in.get()

                if msg_in.action == "execute":
                    #self.debug("Starting execute")
                    success = self.execute(msg_in, conn)

                    msg_out = QueueMsg("finished", self.worker_idd)
                    msg_out.success = success
                    queue_master.put(msg_out)

                    if not conn.is_alive:
                        conn = self.connection_builder()

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


    def execute(self, msg_in, conn):

        task:Task = msg_in.task

        # Prepare the initrc

        variables = copy.copy(self.env_variables)
        variables["WUP_WORK_DIR"] = task.work_dir

        for v in task.combination:
            variables[v["n"]] = str(v["v"])

        initrc = [b"export %s=\"%s\"" % (a.encode(), b.encode()) for a, b in variables.items()]
        initrc.insert(0, b"cd \"%s\"" % task.work_dir.encode())

        # Prepare the command line we will execute

        cmdline = " ; ".join(task.cmdlines).encode()

        # Execute this task

        task.started_at = datetime.now()
        task.success, task.output, task.status = conn.execute(initrc, cmdline)
        task.ended_at = datetime.now()
        task.duration = (task.ended_at - task.started_at).total_seconds()

        # Create the task folder and clean any old .done file

        done_filepath = os.path.join(task.output_dir, ".done")
        os.makedirs(task.output_dir, exist_ok=True)
        if os.path.exists(done_filepath):
            os.remove(done_filepath)

        # Dump task info

        info = copy.copy(task.__dict__)
        info["env_variables"] = variables
        del info["output"]

        filepath = os.path.join(task.output_dir, "info.yml")
        with open(filepath, "w") as fout:
            yaml.dump(info, fout, default_flow_style=False)
        
        # Dump task output

        filepath = os.path.join(task.output_dir, "output.txt")
        with open(filepath, "wb") as fout:
            fout.writelines(task.output)

        # Create .done file if the task succeded

        if task.success:
            with open(done_filepath, 'a'):
                os.utime(done_filepath, None)

        # Write output to stdout if the task failed

        else:
            critical("Task %d has failed. Exit code: %s" % (task.task_idd, task.status))
            for line in task.output:
                os.write(sys.stdout.fileno(), line)
            critical("--- END OF FAILED OUTPUT ---")

        return task.success


class ClusterBurn():

    def __init__(self, tasks_filter, nodes_filter, 
            output_dir, redo_tasks, recreate, 
            experiments, clusters):

        self.output_folder = expand_path(output_dir)
        self.tasks_filter = tasks_filter
        self.nodes_filter = nodes_filter
        self.experiments = experiments
        self.redo_tasks = redo_tasks
        self.recreate = recreate
        self.clusters = clusters


    def start(self):
        os.makedirs(self.output_folder, exist_ok=True)

        self._summary(self.experiments, self.clusters)
        self._validate_signature()
        self.tasks = self._create_tasks()
        self.workers = self._create_workers()
        self._burn()


    def _summary(self, experiments, clusters):

        # Display experiments
        total_tasks = 0
        experiment: Experiment

        for experiment in experiments:
            variables = experiment.vars
            current = 1

            for var in variables:
                values = var.values
                ll = len(values)
                print("\t%s (%d) : %s" % (var.name, ll, str(values)))
                current *= ll
            
            current *= experiment.repeat
            print(f"Experiment '{experiment.name}' has {len(variables)} variable(s) and {current} task(s)")
            total_tasks += current
        
        print(f"Total number of tasks: {total_tasks}")

        # Display clusters
        total_nodes = 0
        total_workers = 0
        node:Node = None
        cluster:Cluster = None

        for cluster in clusters:
            total_nodes += len(cluster.nodes)
            print(f"\tCluster '{cluster.name}' has {len(cluster.nodes)} worker(s)")

            for node in cluster.nodes:
                total_workers += node.workers
                print(f"\tNode '{node.name}' has {node.workers} worker(s)")
        
        print(f"Total number of clusters: {len(clusters)}")
        print(f"Total number of nodes: {total_nodes}")
        print(f"Total number of workers: {total_workers}")


    def _validate_signature(self):

        key = hashlib.md5()

        key.update(str(self.experiments).encode())

        signature = base64.b64encode(key.digest()).decode("utf-8")

        self.output_folder
        self.tasks_filter
        self.nodes_filter
        self.experiments
        self.redo_tasks
        self.recreate
        self.clusters

        info = {
            "output_folder": self.output_folder,
            "tasks_filter": self.tasks_filter,
            "nodes_filter": self.nodes_filter,
            "experiments": self.experiments,
            "redo_tasks": self.redo_tasks,
            "recreate": self.recreate,
            "clusters": self.clusters,
            "signature": signature
        }

        info_filepath = os.path.join(self.output_folder, "info.yml")

        try:
            with open(info_filepath, "r") as fin:
                other = yaml.load(fin, Loader=yaml.FullLoader)
        except:
            other = None

        if other and "signature" in other and other["signature"] != signature:
            if self.recreate:
                clean_folder(self.output_folder)
            else:
                error("The output folder contains a different output configuration. Provide an empty folder or add the parameter --recreate to overwrite this one")
            
        with open(info_filepath, "w") as fout:
            yaml.dump(info, fout, default_flow_style=False)


    def _create_tasks(self, experiments, output_folder, repeat, redo_tasks, tasks_filter):

        print("Creating tasks...")

        e:Experiment = None
        combination_idd = -1
        experiment_idd = -1
        #run_idd = -1
        task_idd = -1
        tasks = []

        for e in experiments:

            experiment_idd += 1

            experiment_filepath = os.path.join(output_folder, "experiments", e.name)
            info_filepath = os.path.join(experiment_filepath, "info.yml")
            os.makedirs(experiment_filepath, exist_ok=True)

            info = {
                "experiment_name": e.name,
                "workdir": e.workdir,
                "commands": e.cmd,
                "repeat": e.repeat,
                "max_tries": e.max_tries,
                "variables": [
                    { 
                        "name": v.name,
                        "values": v.values 
                    } for v in e.vars
                ]
            }

            with open(info_filepath, "w") as fout:
                yaml.dump(info, fout, default_flow_style=False)

            for combination in combine_variables(e.vars):
                combination_idd += 1

                for repeat_idd in range(repeat):
                    task_idd += 1

                    if tasks_filter and not any(a <= task_idd < b for a, b in tasks_filter):
                        continue

                    task_output_folder = os.path.join(experiment_filepath, str(task_idd))

                    if not redo_tasks and os.path.exists(os.path.join(task_output_folder, ".done")):
                        continue

                    task = Task(e.name, task_output_folder, e.workdir, experiment_idd, combination_idd, repeat_idd, task_idd, combination, e.cmd)
                    tasks.append(task)

        if not tasks:
            error("No tasks to do")
        
        return tasks


    def _create_workers(self, clusters):

        print("Starting cluster...")

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
        
        return workers


    def _burn(self):
        self.queue = Queue()

        self.todo = copy.copy(self.tasks)
        self.doing = []
        self.done = []
        self.given_up = []

        self.idle = []
        self.ended = []

        len_todo = len(str(len(self.todo)))
        len_workers = len(str(len(self.workers)))
        

        # Start loop
        info("Starting %d worker(s)" % len(self.workers))
        for worker in self.workers:
            worker.start(self.queue)

        # Main loop
        try:
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

                msg = "%s %s %s %s %s" % (d, l1, l2, l3, l4)
                print(msg)

                #info("|MASTER| Status %d/%d/%d" % (len(self.todo), len(self.doing), len(self.done)))
                #info("|MASTER| Message %s from %d" % (msg_in.action, msg_in.source))

                if msg_in.action == "ready":
                    self._ready(msg_in)
                
                elif msg_in.action == "finished":
                    self._finished(msg_in)
                
                else:
                    warn("Unknown action:", msg_in.action)
            
            info("Completed")
        except KeyboardInterrupt:
            print("Operation interrupted")
            return

        print()

        # Ending loop
        try:
            info("Terminating workers...")
            # Sending TERM signal
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

            info("Terminated")
        except KeyboardInterrupt:
            print("Operation interrupted")
            return


    def _ready(self, msg_in):
        if self.todo:
            msg_out = QueueMsg("execute")
            msg_out.task = self.todo.pop()
            msg_out.task.assigned_to = msg_in.source
            msg_out.task.tries += 1

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

        if msg_in.success:
            self.done.append(task)
            return

        if task.tries >= 3:
            warn("Giving up on task %d too many fails" % task.task_idd)
            self.given_up.append(task)
            return
        
        if not self.idle:
            self.todo.append(task)
            return

        target = self.idle.pop()

        msg_out = QueueMsg("execute")
        msg_out.task = task
        msg_out.task.assigned_to = target
        msg_out.task.tries += 1

        self.workers[target].queue.put(msg_out)
