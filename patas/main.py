#!/usr/bin/env python3

try:
    from . import consts as c
except:
    from patas import consts as c

from patas.schemas import Cluster, Experiment, Node, ListVariable, ArithmeticVariable, GeometricVariable, load_cluster, load_experiment
from patas.utils import error, node_cpu_count, abort
from patas.parse import ExperimentParser, Pattern
from patas.query_engine import QueryEngine
from patas.grid_explorer import GridExplorer
from patas import argparsers
from patas import graphics

from multiprocessing import cpu_count
import sys



def create_experiments(args):

    experiments = []
    
    # If experiment parameters are provided, create an experiment for them

    experiment = Experiment()

    if args.name:
        experiment.name = args.name

    if args.repeat:
        experiment.repeat = args.repeat
    
    if args.workdir:
        experiment.workdir = args.workdir
    else:
        from os import environ
        experiment.workdir = environ['PWD']
    
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
    
    return experiments


def create_clusters(args):

    clusters = []

    # If cluster files are provided, we will use them

    if args.cluster:
        for filepath in args.cluster:
            print(filepath)
            cluster = load_cluster(filepath)
            clusters.append(cluster)
    
    # If nodes are provided, we will add them to the QuickCluster

    if args.node:
        
        cluster = Cluster()
        cluster.name = 'cluster'
        clusters.append(cluster)

        for i, node_params in enumerate(args.node):

            node = Node()
            node.name = f'node{i}'

            address      = node_params[0]
            node.workers = int(node_params[1]) if len(node_params) > 1 else None
            node.tags    = node_params[2:] if len(node_params) > 2 else []

            if ':' in address:
                address, port = address.split(':', 1)
                node.port = int(port)
            
            if '@' in address:
                node.user, node.hostname = address.split('@', 1)
                
            else:
                node.hostname = address

            if node.workers is None:
                node.workers = node_cpu_count(node.user, node.hostname, node.port, 1)
                
            cluster.nodes.append(node)

    # If no cluster or node is provided, we will create a simple one based on the local machine

    if not clusters:

        node          = Node()
        node.name     = 'localhost'
        node.hostname = 'localhost'
        node.workers  = cpu_count()

        cluster       = Cluster()
        cluster.name  = 'cluster'

        cluster.nodes.append(node)
        clusters.append(cluster)
    
    return clusters


def create_task_filters(args):

    task_filters = []

    for filters in args.task_filters:
        for task in filters:
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
                    error(f'Invalid attribute for --task-filter: {task}')

            except ValueError:
                error(f'Invalid attribute for --task-filter: {task}')

    return task_filters


def create_node_filters(args):

    return [ x for filters in args.node_filters for x in filters ]


def create_patterns(args):

    return [Pattern(name, pattern) for name, pattern in args.patterns]


def create_linebreakers(args):

    return [Pattern(None, pattern) for pattern in args.linebreakers]


def do_explore_grid(argv):

    args         = argparsers.parse_patas_explore_grid(argv)
    experiments  = create_experiments(args)
    clusters     = create_clusters(args)
    task_filters = create_task_filters(args)
    node_filters = create_node_filters(args)
    gridexec     = GridExplorer(task_filters, node_filters, args.output_folder, args.redo_tasks, args.recreate, args.confirmed, experiments, clusters)

    gridexec.start()


def do_explore_cdeepso(argv):
    abort("CDEEPSO is not implemented yet.")


def do_parse(argv):

    args         = argparsers.parse_patas_parse(argv)
    patterns     = create_patterns(args)
    linebreakers = create_linebreakers(args)
    parser       = ExperimentParser(patterns, linebreakers, True)

    parser.start(args.experiment_folder, args.output_file)

def do_query(argv):
    
    args   = argparsers.parse_patas_query(argv)
    engine = QueryEngine(args.patas_folder)
    engine.query(args.query, args.pretty_print)


def do_draw_heatmap(argv):

    args = argparsers.parse_patas_draw_heatmap(argv)
    graphics.render_heatmap(args.x_column, args.y_column, args.z_column,
                            args.title, args.x_label, args.y_label,
                            args.x_change, args.y_change, args.z_change,
                            args.input_file, args.output_file, 
                            args.z_format, args.size, args.verbose, args.reduce, args.colormap)


def do_draw_lines(args):
    abort("Draw Lines is not implemented yet.")


def do_draw_bars(args):
    abort("Draw Bars is not implemented yet.")


def do_doctor(args):
    abort("doctor is not implemented yet.")


def do_version(args):
    print(f"Patas {c.version}")


def help_main_syntax():
    print("Syntax: patas [explore,parse,query,draw] {ARGS}")


def help_explore_syntax():
    print("Syntax: patas explore [grid,cdeepso] {ARGS}")


def help_draw_syntax():
    print("Syntax: patas draw [heatmap, lines, bars] {ARGS}")


def main(*params):

    args = sys.argv[1:]

    if len(args) == 0:
        help_main_syntax()
    
    elif args[0] == 'explore':

        if len(args) == 1:
            help_explore_syntax()
        
        elif args[1] == 'grid':
            do_explore_grid(args[2:])

        elif args[1] == 'cdeepso':
            do_explore_cdeepso(args[2:])

        else:
            help_explore_syntax()

    elif args[0] == 'parse':
        do_parse(args[1:])

    elif args[0] == 'query':
        do_query(args[1:])

    elif args[0] == 'draw':

        if len(args) == 1:
            help_draw_syntax()
        
        elif args[1] == 'heatmap':
            do_draw_heatmap(args[2:])

        elif args[1] == 'lines':
            do_draw_lines(args[2:])

        elif args[1] == 'bars':
            do_draw_bars(args[2:])

        else:
            help_draw_syntax()

    elif args[0] == 'doctor':
        do_doctor(args[1:])

    elif args[0] == '-v' or args[0] == '--version':
        do_version()

    elif args[0] == '-h' or args[0] == '--help':
        help_main_syntax()

    else:
        help_main_syntax()


if __name__ == "__main__":
    main()
