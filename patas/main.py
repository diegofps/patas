#!/usr/bin/env python3

try:
    from . import consts as c
except:
    from patas import consts as c

from patas.schemas import Cluster, Experiment, Node, ListVariable, ArithmeticVariable, GeometricVariable, load_cluster, load_experiment
from patas.grid_exec import GridExec
from patas.utils import error

from multiprocessing import cpu_count

import argparse
import sys



def show_main_syntax():
    print("Syntax: patas [exec,parse,doctor] {ARGS}")

def show_exec_syntax():
    print("Syntax: patas exec [grid] {ARGS}")
 
def do_version(args):
    print(f"Patas {c.version}")

def do_exec_grid(argv):
    
    # exec grid parser

    parser = argparse.ArgumentParser(
                        prog='patas exec grid',
                        description='Execute a program permutating its input parameters.',
                        epilog="Check the README.md to learn more tips on how to use this feature: https://github.com/diegofps/patas/blob/main/README.md",
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    # General parameters

    parser.add_argument('--cluster',
                        type=str,
                        metavar='FILEPATH',
                        dest='cluster',
                        help="path to a cluster file",
                        action='append')

    parser.add_argument('--experiment',
                        type=str,
                        metavar='FILEPATH',
                        dest='experiment',
                        help="path to an experiment file",
                        action='append')

    parser.add_argument('--redo',
                        dest='redo_tasks',
                        help="forces patas to redo all tasks when an experiment is executed again",
                        action='store_true')

    parser.add_argument('--recreate',
                        dest='recreate',
                        help="recreate the entire output folder if it contains a different experiment configuration",
                        action='store_true')

    parser.add_argument('--filter-tasks',
                        type=str,
                        default=[],
                        metavar='A:B',
                        dest='task_filters',
                        help="restricts the tasks that will be executed [A:B, A:, :B, :]",
                        action='append')

    parser.add_argument('--filter-nodes',
                        type=str,
                        default=[],
                        metavar='TAG',
                        nargs='*',
                        dest='node_filters',
                        help="filter nodes that match these tags (AND)",
                        action='store')

    parser.add_argument('--node',
                        type=str,
                        nargs='*',
                        metavar='NAME USER@HOST:PORT WORKERS TAG1 ...',
                        dest='node',
                        help="adds a machine with the given number of workers to the cluster",
                        action='append')

    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        help="allow debug log messages to be displayed",
                        action='store_true')

    parser.add_argument('-q', '--quiet',
                        default=None,
                        dest='quiet',
                        help="display only warning messages and above",
                        action='store_true')

    parser.add_argument('-y',
                        dest='confirmed',
                        help="skip confirmation before starting the tasks",
                        action='store_true')

    parser.add_argument('-o',
                        type=str,
                        default='./tmp',
                        metavar='FOLDER',
                        dest='output_folder',
                        help="folder to store the program outputs",
                        action='store')


    # Quick Experiment parameters

    parser.add_argument('--vl',
                        type=str,
                        nargs='*',
                        default=[],
                        metavar='VAL',
                        dest='var_list',
                        help="defines an input variable that can assume a fixed number of values",
                        action='append')

    parser.add_argument('--va',
                        type=str,
                        nargs=4,
                        default=[],
                        metavar=('NAME', 'MIN', 'MAX', 'FACTOR'),
                        dest='var_arithmetic',
                        help="defines an input variable that grows according to an arithmetic progression",
                        action='append')

    parser.add_argument('--vg',
                        type=str,
                        nargs=4,
                        default=[],
                        metavar=('NAME', 'MIN', 'MAX', 'FACTOR'),
                        dest='var_geometric',
                        help="defines an input variable that grows according to a geometric progression",
                        action='append')

    parser.add_argument('--repeat',
                        type=int,
                        metavar='R',
                        default='1',
                        dest='repeat',
                        help="number of times that each combination must be executed",
                        action='store')

    parser.add_argument('--max-tries',
                        type=int,
                        metavar='T',
                        dest='max_tries',
                        help="maximum number of retries after a task has failed",
                        action='store')

    parser.add_argument('--workdir',
                        type=str,
                        metavar='W',
                        dest='workdir',
                        help="The working directory in the remote machines that will start the tasks",
                        action='store')

    parser.add_argument('--cmd',
                        type=str,
                        metavar='CMD',
                        required=True,
                        dest='cmd',
                        help="command to be executed. Use {VAR_NAME} to replace its parameters with a named variable",
                        action='append')

    args = parser.parse_args(args=argv)

    experiments = []
    clusters = []

    # If experiment parameters are provided, create an experiment for them

    experiment = Experiment()

    experiment.name = 'QuickExperiment'

    if args.repeat:
        experiment.repeat = args.repeat
    
    if args.workdir:
        experiment.workdir = args.workdir
    
    if args.cmd:
        experiment.cmd = args.cmd

    if args.max_tries:
        experiment.max_tries = args.max_tries

    for values in args.var_list:
        var = ListVariable()
        var.name = values[0]
        var.values = values[1:]
        experiment.vars.append(var)

    for name, min, max, factor in args.var_arithmetic:
        var = ArithmeticVariable()
        var.name = name
        var.min = min
        var.max = max
        var.factor = factor
        var.update()
        experiment.vars.append(var)

    for name, min, max, factor in args.var_geometric:
        var = GeometricVariable()
        var.name = name
        var.min = min
        var.max = max
        var.factor = factor
        var.update()
        experiment.vars.append(var)

    if experiment.cmd or experiment.vars:
        experiments.append(experiment)

    # If experiment files are provided, load all of them

    if args.experiment:
        for filepath in args.experiment:
            experiment = load_experiment(filepath)
            experiments.append(experiment)
    
    # If cluster files are provided, we will use them

    if args.cluster:
        for filepath in args.cluster:
            print(filepath)
            cluster = load_cluster(filepath)
            clusters.append(cluster)
    
    # If nodes are provided, we will add them to the QuickCluster

    if args.node:
        
        cluster = Cluster()
        cluster.name = 'QuickCluster'
        clusters.append(cluster)

        for i, node_params in enumerate(args.node):

            node = Node()
            node.name = f'node{i}'

            address      = node_params[0]
            node.workers = int(node_params[1]) if len(node_params) > 1 else 1
            node.tags    = node_params[2:] if len(node_params) > 2 else []

            if ':' in address:
                address, port = address.split(':', 1)
                node.port = int(port)
            
            if '@' in address:
                node.user, node.hostname = address.split('@', 1)
                
            else:
                node.hostname = address

            cluster.nodes.append(node)

    # If no cluster or node is provided, we will create a simple one for the local machine

    if not clusters:

        node          = Node()
        node.name     = 'LocalMachine'
        node.hostname = 'localhost'
        node.workers  = cpu_count()

        cluster       = Cluster()
        cluster.name  = 'QuickCluster'

        cluster.nodes.append(node)

        clusters.append(cluster)

    # Prepare the tasks_filter

    task_filters = []

    for task in args.task_filters:
        try:

            cells = task.split(':')

            if len(cells) == 2:
                i1 = int(cells[0]) if cells[0] else 0
                i2 = int(cells[1]) if cells[1] else float('inf')
                task_filters.append((i1, i2))

            elif len(cells) == 1:
                i1 = int(cells[0]) if cells[0] else 0
                task_filters.append((i1, i1+1))

            else:
                error(f'Invalid --task-filter: {task}')

        except ValueError:
            error(f'Invalid --task-filter: {task}')

    # Create the ClusterBurn

    print(args)
    burn = GridExec(task_filters, args.node_filters, args.output_folder, args.redo_tasks, args.recreate, args.confirmed, experiments, clusters)
    burn.start()

def do_parse(args):
    raise NotImplementedError("parse is not implemented yet.")

def do_doctor(args):
    raise NotImplementedError("doctor is not implemented yet.")

def do_exec_cdeepso(args):
    raise NotImplementedError("CDEEPSO is not implemented yet.")

def do_plot(args):
    raise NotImplementedError("Plotting is not implemented yet.")


def main(*params):
    args = sys.argv[1:]

    if len(args) == 0:
        show_main_syntax()
    
    elif args[0] == 'exec':

        if len(args) == 1:
            show_exec_syntax()
        
        elif args[1] == 'grid':
            do_exec_grid(args[2:])

        elif args[1] == 'cdeepso':
            do_exec_cdeepso(args[2:])

        else:
            show_exec_syntax()

    elif args[0] == 'parse':
        do_parse(args[1:])

    elif args[0] == 'plot':
        do_doctor(args[1:])

    elif args[0] == 'doctor':
        do_doctor(args[1:])

    elif args[0] == '-v' or args[0] == '--version':
        do_version()

    elif args[0] == '-h' or args[0] == '--help':
        show_main_syntax()

    else:
        show_main_syntax()


if __name__ == "__main__":
    main()
