#!/usr/bin/env python3

import argparse
import sys

try:
    from . import consts as c
except:
    from patas import consts as c

from .schemas import Cluster, Experiment, Node, ListVariable, ArithmeticVariable, GeometricVariable, load_cluster, load_experiment


def show_main_syntax():
    print("Syntax: patas [exec,parse,doctor] {ARGS}")

def show_exec_syntax():
    print("Syntax: patas exec [grid] {ARGS}")
 
def do_version(args):
    print(f"Patas {c.version}")

def do_exec_grid(argv):
    
    parser = argparse.ArgumentParser(
                        prog='patas exec grid',
                        description='Execute a program permutating its input parameters.',
                        epilog="Check the README.md to learn more tips on how to use this feature: https://github.com/diegofps/patas/blob/main/README.md",
                        formatter_class=argparse.RawDescriptionHelpFormatter)

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
                        dest='redo',
                        help="forces patas to redo all tasks when an experiment is executed again",
                        action='store_true')

    parser.add_argument('--recreate',
                        metavar='FOLDER',
                        dest='recreate',
                        help="recreate the entire output folder if it contains a different experiment configuration",
                        action='store_true')

    parser.add_argument('--filter-tasks',
                        type=str,
                        metavar='A:B',
                        dest='filter_tasks',
                        help="restricts the tasks that will be executed [A:B, A:, :B, :]",
                        action='append')

    parser.add_argument('--filter-nodes',
                        type=str,
                        metavar='TAG',
                        nargs='*',
                        dest='filter_nodes',
                        help="filter nodes that match these tags (AND)",
                        action='store')

    parser.add_argument('--node',
                        type=str,
                        metavar=('NAME', 'USER@HOST:PORT', 'PROCS', 'TAG1', '...'),
                        dest='cluster',
                        help="adds a worker machine to the cluster",
                        action='append')

    parser.add_argument('-v', '--verbose',
                        default=None,
                        dest='verbose',
                        help="allow debug log messages to be displayed",
                        action='store_true')

    parser.add_argument('-q', '--quiet',
                        default=None,
                        dest='quiet',
                        help="display only warning messages and above",
                        action='store_true')

    parser.add_argument('-o',
                        type=str,
                        metavar='FOLDER',
                        dest='raw_data_out',
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

    if args.repeat:
        experiment.repeat = args.repeat
    
    if args.workdir:
        experiment.workdir = args.workdir
    
    if args.cmd:
        experiment.cmd = args.cmd

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
            cluster = load_cluster(filepath)
            clusters.append(cluster)
    
    # Otherwise, we will create a simple one for the local machine
    else:
        from multiprocessing import cpu_count

        node = Node()
        node.name = 'LocalMachine'
        node.hostname = 'localhost'
        node.procs = cpu_count()

        cluster = Cluster()
        cluster.nodes.append(node)

    # Create the ClusterBurn 
    print(args)

    #(tasks_filter, nodes_filter, output_dir, redo_tasks, recreate, experiments, clusters)

    burn = ClusterBurn()
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
