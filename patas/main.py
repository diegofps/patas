#!/usr/bin/env python3

try:
    from . import consts as c
except:
    from patas import consts as c

from collections import defaultdict
from patas.utils import error, node_cpu_count, abort, warn
from patas import argparsers
from patas import schemas

import sys


BASIC_OPTIONS   = ['explore', 'parse', 'query', 'draw', 'doctor']
DRAW_OPTIONS    = ['heatmap', 'lines', 'lines_3d', 'bars', 'bars_3d', 'boxplot', 'violin', 'scatter', 'scatter_3d', 'surface', 'pie']
EXPLORE_OPTIONS = ['grid', 'cdeepso']


def parse_base_experiment(args, experiment:schemas.BaseExperimentSchema):

    if args.name:
        experiment.name = args.name

    if args.repeat:
        experiment.repeat = args.repeat
    
    if args.workdir:
        experiment.workdir = args.workdir
    else:
        from os import environ
        pwd  = environ.get('PWD', None)
        home = environ.get('HOME', None)

        if home and pwd.startswith(home):
            experiment.workdir = '$HOME' + pwd[len(home):]
        else:
            experiment.workdir = pwd
    
    if args.cmd:
        experiment.cmd = args.cmd

    if args.max_tries:
        experiment.max_tries = args.max_tries

    if args.redo_tasks:
        experiment.redo_tasks = args.redo_tasks

def append_grid_experiment(args, experiments):

    experiment = schemas.GridExperimentSchema()

    parse_base_experiment(args, experiment)
    
    for values in args.var_list:
        var        = schemas.ListVariableSchema()
        var.name   = values[0]
        var.values = values[1:]
        experiment.vars.append(var)

    for name, min, max, step in args.var_arithmetic:
        var      = schemas.ArithmeticVariableSchema()
        var.name = name
        var.min  = float(min)  if '.' in min  else int(min)
        var.max  = float(max)  if '.' in max  else int(max)
        var.step = float(step) if '.' in step else int(step)
        var.update()
        experiment.vars.append(var)

    for name, min, max, step in args.var_geometric:
        var        = schemas.GeometricVariableSchema()
        var.name   = name
        var.min    = float(min)  if '.' in min  else int(min)
        var.max    = float(max)  if '.' in max  else int(max)
        var.factor = float(step) if '.' in step else int(step)
        var.update()
        experiment.vars.append(var)

    if args.score_pattern:
        warn("GridExperiment is not compatible with parameter --score-pattern")

    if experiment.cmd and experiment.vars:
        experiments.append(experiment)
    
    return experiments


def append_cdeepso_experiment(args, experiments:list):
    
    experiment = schemas.CDEEPSOExperimentSchema()

    parse_base_experiment(args, experiment)
    
    if args.score_pattern:
        experiment.score_pattern = args.score_pattern
    
    if args.var_list:
        warn("CDEEPSOExperiment is not compatible with parameter --vl")

    if args.var_arithmetic:
        warn("CDEEPSOExperiment is not compatible with parameter --va")

    if args.var_geometric:
        warn("CDEEPSOExperiment is not compatible with parameter --vg")

    if experiment.cmd and experiment.vars:
        experiments.append(experiment)
    
    return experiments


def load_experiments_from_files(args):

    experiments = []
    
    # If experiment files are provided, load all of them

    if args.experiment:
        for filepath in args.experiment:
            experiment = schemas.load_experiment(filepath)
            experiments.append(experiment)
    
    return experiments


def create_clusters(args):

    from patas.schemas import ClusterSchema, NodeSchema, load_cluster

    clusters = []

    # If cluster files are provided, we will use them

    if args.cluster:
        for filepath in args.cluster:
            print(filepath)
            cluster = load_cluster(filepath)
            clusters.append(cluster)
    
    # If nodes are provided, we will add them to the QuickCluster

    if args.node:
        
        cluster = ClusterSchema()
        cluster.name = 'cluster'
        clusters.append(cluster)

        for i, node_params in enumerate(args.node):

            node = NodeSchema()
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

        from multiprocessing import cpu_count

        node          = NodeSchema()
        node.name     = 'localhost'
        node.hostname = 'localhost'
        node.workers  = cpu_count()

        cluster       = ClusterSchema()
        cluster.name  = 'cluster'

        cluster.nodes.append(node)
        clusters.append(cluster)
    
    return clusters


def create_task_filters(args):

    task_filters = defaultdict(list)

    for filters in args.task_filters:
        for slice in filters:
            try:

                cells = slice.split(':')

                if len(cells) == 3:
                    xp =     cells[0]  if cells[0] else args.type
                    i1 = int(cells[1]) if cells[1] else 0
                    i2 = int(cells[2]) if cells[2] else float('inf')
                
                elif len(cells) == 2:
                    xp = args.type
                    i1 = int(cells[0]) if cells[0] else 0
                    i2 = int(cells[1]) if cells[1] else float('inf')

                elif len(cells) == 1:
                    xp = args.type
                    i1 = int(cells[0]) if cells[0] else 0
                    i2 = i1+1

                else:
                    error(f'Invalid attribute for --task-filter: {slice}')
                
                task_filters[xp].append((i1, i2))

            except ValueError:
                error(f'Invalid attribute for --task-filter: {slice}')

    return task_filters


def create_node_filters(args):

    return [ x for filters in args.node_filters for x in filters ]


def create_patterns(args):

    from patas.parse import Pattern

    return [Pattern(name, pattern) for name, pattern in args.patterns]


def create_linebreakers(args):

    from patas.parse import Pattern

    return [Pattern(None, pattern) for pattern in args.linebreakers]


def do_explore(argv):

    from patas.scheduler import Scheduler

    args         = argparsers.parse_patas_explore(argv)
    clusters     = create_clusters(args)
    task_filters = create_task_filters(args)
    node_filters = create_node_filters(args)
    experiments  = load_experiments_from_files(args)

    if args.type == 'grid':
        append_grid_experiment(args, experiments)

    elif args.type == 'cdeepso':
        append_cdeepso_experiment(args, experiments)

    for x in experiments:
        x.task_filters = task_filters.pop(x.name, [])
    
    for idd, x in enumerate(experiments):
        x.experiment_idd = idd

    if task_filters:
        names = ', '.join([x for x in task_filters])
        warn(f"Ignoring task-filters for the following experiments: {names}")

    scheduler = Scheduler(node_filters, args.output_folder, args.redo_tasks, args.confirmed, experiments, clusters, args.quiet)
    scheduler.start()


def do_parse(argv):

    from patas.parse import ExperimentParser

    args         = argparsers.parse_patas_parse(argv)
    patterns     = create_patterns(args)
    linebreakers = create_linebreakers(args)
    parser       = ExperimentParser(patterns, linebreakers, True)

    parser.start(args.experiment_folder, args.output_file)


def do_query(argv):

    from patas.query_engine import QueryEngine
    
    args   = argparsers.parse_patas_query(argv)
    engine = QueryEngine(args.patas_folder)
    engine.query(args.query, args.pretty_print)


def do_draw_heatmap(argv):

    from patas import graphics

    args = argparsers.parse_patas_draw_heatmap(argv)

    graphics.render_heatmap(args.x_column, args.y_column, args.z_column,
                            args.title, args.x_label, args.y_label, args.r_label,
                            args.x_change, args.y_change, args.z_change, args.r_format, 
                            args.input_file, args.output_file, 
                            args.size, args.r_function, args.colormap, 
                            args.verbose)


def do_draw_lines(argv):
    
    from patas import graphics

    args = argparsers.parse_patas_draw_lines(argv)

    lines = [
        (line.x_column, line.y_column, line.x_change, line.y_change, line.r_function, line.label, line.style, line.marker, line.marker_size) 
        for line in args.lines
    ]

    graphics.render_lines(lines, args.title, args.size, 
                          args.x_label, args.r_label, 
                          args.input_file, args.output_file, 
                          args.show_grid, args.border, args.show_error, 
                          args.ticks, args.ticks_format, args.legend_location,
                          args.verbose)


def do_draw_lines_3d(argv):
    abort("Draw lines_3d is not implemented yet.")


def do_draw_bars(argv):
    
    from patas import graphics

    args = argparsers.parse_patas_draw_bars(argv)

    graphics.render_bars(args.x_column, args.y_column, 
                         args.title, args.x_label, args.r_label, 
                         args.x_change, args.y_change, args.r_format, 
                         args.input_file, args.output_file, 
                         args.size, args.r_function, args.bar_color, args.bar_size, args.horizontal, args.show_grid, 
                         args.ticks, args.ticks_format, args.border, args.show_error,
                         args.verbose)


def do_draw_bars_3d(args):
    abort("Draw bars_3d is not implemented yet.")


def do_draw_boxplot(args):
    abort("Draw boxplot is not implemented yet.")


def do_draw_violin(args):
    abort("Draw violin is not implemented yet.")


def do_draw_scatter(args):
    abort("Draw scatter is not implemented yet.")


def do_draw_scatter_3d(args):
    abort("Draw scatter_3d is not implemented yet.")


def do_draw_surface(args):
    abort("Draw surface is not implemented yet.")


def do_draw_pie(args):
    abort("Draw pie is not implemented yet.")


def do_doctor(args):
    abort("doctor is not implemented yet.")


def help_main_syntax():
    print(f"Patas {c.version}")
    print(f"Syntax: patas [{','.join(BASIC_OPTIONS)}] ...")


def help_draw_syntax():
    print(f"Syntax: patas draw [{','.join(DRAW_OPTIONS)}] ...")


def main(*params):

    # parser.add_subparsers()

    args = sys.argv[1:]

    if len(args) == 0 or not args[0] in BASIC_OPTIONS:
        help_main_syntax()
        
    elif args[0] == 'draw':

        if len(args) == 1 or not args[1] in DRAW_OPTIONS:
            help_draw_syntax()
        
        globals()['do_draw_' + args[1]](args[2:])

    else:
        globals()['do_' + args[0]](args[1:])


if __name__ == "__main__":
    main()
