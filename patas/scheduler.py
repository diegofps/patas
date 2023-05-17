from .utils import expand_path, error, warn, info, debug, critical, abort, readlines, estimate, human_time, quote, colors
from .schemas import ClusterSchema, NodeSchema, Task

from multiprocessing import Process, Queue
from subprocess import Popen, PIPE, STDOUT
from datetime import datetime

import select
import shlex
import copy
import time
import pty
import sys
import os


KEY_SSH_ON  = b'74ffc7c4-a6ad-4315-94cb-59d045a230c0'
KEY_SSH_OFF = b'93dfc971-fa64-4beb-a24e-d8874738b9ca'
KEY_CMD_ON  = b'15e6896c-3ea7-42a0-aa32-23e2ab3c0e12'
KEY_CMD_OFF = b'e04a4348-8092-46a6-8e0c-d30d10c86fb3'

build_echo_cmd = lambda x: b" echo -e \"%s\"" % x.replace(b"-", b"-\b-")

ECHO_SSH_ON  = build_echo_cmd(KEY_SSH_ON)
ECHO_SSH_OFF = build_echo_cmd(KEY_SSH_OFF)
ECHO_CMD_ON  = build_echo_cmd(KEY_CMD_ON)
ECHO_CMD_OFF = b" echo -en \"\n $? %s\"" % KEY_CMD_OFF.replace(b"-", b"-\b-")


class WorkerMessage(dict):

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

        p1 = b" ; ".join(initrc)
        p3 = b" ; ".join(cmds)

        cmd_str = b" %s ; %s " % (p1, p3)
        cmd_str = "bash -c " + quote(cmd_str.decode('utf-8'))
        
        ps = Popen(shlex.split(cmd_str), stdout=PIPE, stderr=STDOUT)

        status = ps.wait()
        stdout = ps.stdout.read()

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

        return (status == "0"), b'\n'.join(lines[output_start:output_end]), status


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

    def run(self, queue_in, queue_master):

        try:
            executor = self.executor_builder()

            msg_out = WorkerMessage("ready", self.worker_idd)
            queue_master.put(msg_out)
            
            while True:
                msg_in = queue_in.get()

                if msg_in.action == "execute":
                    success = self.execute(msg_in, executor)

                    msg_out = WorkerMessage("finished", self.worker_idd)
                    msg_out.success = success
                    queue_master.put(msg_out)

                    if not executor.is_alive:
                        executor = self.executor_builder()

                    msg_out = WorkerMessage("ready", self.worker_idd)
                    queue_master.put(msg_out)
                
                elif msg_in.action == "terminate":
                    break
                
                else:
                    warn("Unknown action:", msg_in.action)
            
            msg_out = WorkerMessage("ended", self.worker_idd)
            queue_master.put(msg_out)
        except KeyboardInterrupt:
            pass

    def execute(self, msg_in, executor):

        task:Task = msg_in.task

        # Prepare the initrc

        task.env_variables = copy.copy(self.env_variables)
        task.env_variables["PATAS_WORK_DIR"] = task.work_dir

        for k,v in task.combination.items():
            task.env_variables["PATAS_VAR_" + k] = str(v)

        initrc = [b"export %s=\"%s\"" % (a.encode(), b.encode()) for a, b in task.env_variables.items()]

        if task.work_dir:
            initrc.insert(0, b"cd \"%s\"" % task.work_dir.encode())

        # Prepare the command line we will execute

        cmdline = " ; ".join(task.commands).encode()

        # Execute this task

        task.started_at = datetime.now()
        task.success, task.output, task.status = executor.execute(initrc, cmdline)
        task.ended_at = datetime.now()
        task.duration = (task.ended_at - task.started_at).total_seconds()

        # Return True if the task succeeded

        return task.success


class Scheduler():

    def __init__(self, node_filters, output_dir, redo_tasks, confirmed, experiments, clusters):

        self.output_folder = expand_path(output_dir)
        self.node_filters  = node_filters
        self.experiments   = experiments
        self.redo_tasks    = redo_tasks
        self.confirmed     = confirmed
        self.clusters      = clusters
        self.todo          = []

        self.workers:list[WorkerProcess] = None

    def start(self):

        os.makedirs(self.output_folder, exist_ok=True)

        self.show_summary(self.experiments, self.clusters, self.confirmed)
        self.workers = self._create_workers(self.clusters, self.node_filters)
        self._exec()

    def push_task(self, task):
        self.todo.append(task)

    def show_summary(self, experiments, clusters, confirmed):

        # Display experiments

        print(colors.white("\n --- Experiments --- \n"))

        total_tasks = 0
        for experiment in experiments:
            experiment.show_summary()
            total_tasks += experiment.number_of_tasks()
        
        # Display clusters

        print(colors.white("\n --- Clusters --- \n"))

        total_nodes   = 0
        total_workers = 0
        for cluster in clusters:
            cluster.show_summary()
            total_nodes   += cluster.number_of_nodes()
            total_workers += cluster.number_of_workers()
            
        # Display total numbers and estimations

        print(colors.white("\n --- Overview --- \n"))

        print(f"Redo:          {self.redo_tasks}")
        print(f"Node filters:  {self.node_filters}")
        print(f"Output folder: {self.output_folder}")

        print()

        print(f"Number of experiments: {len(experiments)}")
        print(f"Number of clusters:    {len(clusters)}")
        print(f"Number of nodes:       {total_nodes}")
        print(f"Number of workers:     {total_workers}")
        print(f"Number of tasks:       {total_tasks}")

        print()

        print('Estimated time to complete if each task takes:')
        print(f"    One second: { estimate(total_tasks, total_workers,        1) }")
        print(f"    One minute: { estimate(total_tasks, total_workers,       60) }")
        print(f"    One hour:   { estimate(total_tasks, total_workers,    60*60) }")
        print(f"    One day:    { estimate(total_tasks, total_workers, 60*60*24) }")

        print()

        # Check experiment signatures

        issues = [x for x in experiments if x.check_signature(self.output_folder)]

        if issues:
            names = ', '.join([x.name for x in issues])
            warn(f"The following experiments have changed their configuration, proceeding will restart all their tasks: {names}")

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
        
        # Clean diverging experiments

        if issues:
            warn("Cleaning diverging experiments...")
            for experiment in issues:
                experiment.clean_output(self.output_folder)

        # Write signature files

        for experiment in experiments:
            experiment.write_signature(self.output_folder)

    def _create_workers(self, clusters, node_filters):

        print("Creating workers...")

        cluster_idd = -1
        worker_idd = -1
        node_idd = -1

        workers = []

        cluster:ClusterSchema = None
        node:NodeSchema = None

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

        self.todo     = []
        self.doing    = []
        self.done     = []
        self.given_up = []

        self.idle     = []
        self.ended    = []

        chars_todo    = 10
        chars_work    = 10
        
        # Start workers

        print()
        info(f"Starting {len(self.workers)} worker(s)")

        for worker in self.workers:
            worker.start(self.queue)
        
        info("Worker(s) started")

        # Start experiments

        for experiment in self.experiments:
            experiment.on_start(self)

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
                l1 = colors.white(" " * (chars_todo - len(l1)) + l1 + " |")
                l2 = colors.white(" " * (chars_work - len(l2)) + l2 + " |")
                l3 = colors.green(" " * (chars_todo - len(l3)) + l3 + " |")
                l4 = colors.red  (" " * (chars_todo - len(l4)) + l4 + " |")

                print(f"{d} {l1} {l2} {l3} {l4}")

                if msg_in.action == "ready":
                    self._on_worker_is_ready(msg_in)
                
                elif msg_in.action == "finished":
                    self._on_task_finished(msg_in)
                
                else:
                    warn("Unknown action:", msg_in.action)
            
            info("Main loop completed")

        except KeyboardInterrupt:

            print("Operation interrupted")
            return

        main_loop_ended_at = datetime.now()
        main_loop_duration = (main_loop_ended_at - main_loop_started_at).total_seconds()
        
        # Send on_finish to all experiments

        for experiment in self.experiments:
            experiment.on_finish()

        # Terminate workers

        terminate_loop_started_at = datetime.now()

        try:
            print()
            info("Releasing workers...")

            # Sending TERMINATE signal

            for worker in self.workers:
                msg = WorkerMessage("terminate")
                worker.queue.put(msg)
            
            # Waiting for ENDED signal

            while len(self.workers) != len(self.ended):

                msg = self.queue.get()

                if msg.action == "ended":

                    self.ended.append(msg.source)

                    d = colors.gray("|%s|" % str(datetime.now()))

                    l1 = str(len(self.ended))
                    l2 = str(len(self.workers))

                    l1 = " " * (chars_work - len(l1)) + l1
                    l2 = " " * (chars_work - len(l2)) + l2

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

        print(f"    Time to execute experiments: {human_time(main_loop_duration)}")
        print(f"    Time to terminate workers:   {human_time(terminate_loop_duration)}")
        print(f"    Tasks requested: {len(self.done) + len(self.given_up)}")
        print(f"    Tasks completed: {len(self.done)}")
        print(f"    Tasks given up:  {len(self.given_up)}")
        print()

    def _on_worker_is_ready(self, msg_in):

        # If there is a task to be done, send it back to the worker
        if self.todo:
            msg_out = WorkerMessage("execute")
            msg_out.task = self.todo.pop()
            msg_out.task.assigned_to = msg_in.source

            self.doing.append(msg_out.task)
            self.workers[msg_in.source].queue.put(msg_out)
        
        # Otherwise, move the worker to the like of idle workers

        else:
            self.idle.append(msg_in.source)

    def _on_task_finished(self, msg_in):

        # Find the position of the task we just received in the message

        for i, x in enumerate(self.doing):
            if x.assigned_to == msg_in.source:
                break
        else:
            warn("Received finished msg but the task was not found inside the doing list")
            return
        
        # Retrieve the task and experiment objects

        task:Task = self.doing[i]
        task.tries += 1
        experiment = self.experiments[task.experiment_idd]
        del self.doing[i]

        # Print stdout if the task has failed

        if not task.success:
            warn("--- TASK %d FAILED WITH EXIT CODE %s ---" % (task.task_idd, task.status))
            os.write(sys.stdout.fileno(), task.output)
            warn("--- END OF FAILED OUTPUT ---")

        # If the task finished successfully, notify its experiment and move it to done

        if msg_in.success:
            self.done.append(task)
            experiment.on_task_completed(self, task)

        # If max_tries has been reached, notify the experiment and move it to given_up

        elif task.tries >= task.max_tries:
            critical(f"Giving up on task {task.task_idd}, max_tries reached.")
            self.given_up.append(task)
            experiment.on_task_completed(self, task)
        
        # If a worker is available, ask it to execute the task again

        elif self.idle:
            target = self.idle.pop()

            msg_out = WorkerMessage("execute")
            msg_out.task = task
            msg_out.task.assigned_to = target

            self.workers[target].queue.put(msg_out)

        # Otherwise, move the task back to todo, we will schedule it again in the future

        else:
            self.todo.append(task)
