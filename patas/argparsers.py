import argparse

DEFAULT_PATAS_OUTPUT_DIR = './patasout'


def parse_patas_explore_grid(argv):

    # argparse for 'patas explore grid'

    parser = argparse.ArgumentParser(
                        prog='patas explore grid',
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
                        nargs='*',
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

    parser.add_argument('-y',
                        dest='confirmed',
                        help="skip confirmation before starting the tasks",
                        action='store_true')

    parser.add_argument('-o',
                        type=str,
                        default=DEFAULT_PATAS_OUTPUT_DIR,
                        metavar='FOLDER',
                        dest='output_folder',
                        help="folder to store the program outputs",
                        action='store')

    # Quick Experiment parameters

    parser.add_argument('--name',
                        type=str,
                        default='grid',
                        metavar='NAME',
                        dest='name',
                        help="changes the name of the experiment folder, default is grid",
                        action='store')

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

    return parser.parse_args(args=argv)


def parse_patas_parse(argv):

    # argparse for 'patas parse'

    parser = argparse.ArgumentParser(
                        prog='patas parse',
                        description='Parse the output files from patas exec and generate a summary in csv',
                        epilog="Check the README.md to learn more tips on how to use this feature: https://github.com/diegofps/patas/blob/main/README.md",
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    # General parameters

    parser.add_argument('-e',
                        type=str,
                        metavar='FOLDERPATH',
                        dest='experiment_folder',
                        required=True,
                        help="path to the experiment folder that must be parsed",
                        action='store')

    parser.add_argument('-o',
                        type=str,
                        metavar='FILEPATH',
                        dest='output_file',
                        help="path to the output csv file",
                        action='store')

    parser.add_argument('-p',
                        type=str,
                        metavar=('OUT_NAME', 'REGEX'),
                        default=[],
                        nargs=2,
                        dest='patterns',
                        help="regex containing a single group capture indicating the data that must be captured",
                        action='append')

    parser.add_argument('-n',
                        type=str,
                        metavar='REGEX',
                        default=[],
                        dest='linebreakers',
                        help="emit a line break in the output csv",
                        action='append')

    return parser.parse_args(args=argv)


def parse_patas_query(argv):

    parser = argparse.ArgumentParser(
                        prog='patas query',
                        description='Execute sql queries in the parsed experiments',
                        epilog="Check the README.md to learn more tips on how to use this feature: https://github.com/diegofps/patas/blob/main/README.md",
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    # General parameters

    parser.add_argument('-i',
                        type=str,
                        default=DEFAULT_PATAS_OUTPUT_DIR,
                        metavar='PATASPATH',
                        dest='patas_folder',
                        help="path to the output folder containing the experiments",
                        action='store')

    parser.add_argument('-m',
                        dest='pretty_print',
                        help="print the output using markdown format",
                        action='store_true')

    parser.add_argument(type=str,
                        metavar='QUERY',
                        dest='query',
                        help="query that must be executed",
                        action='store')
    
    return parser.parse_args(args=argv)


def parse_patas_draw_heatmap(argv):

    parser = argparse.ArgumentParser(
                        prog='patas draw heatmap',
                        description='Draws a heatmap from the input data',
                        epilog="Check the README.md to learn more tips on how to use this feature: https://github.com/diegofps/patas/blob/main/README.md",
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    # INITIAL PARAMETERS

    parser.add_argument('--input', 
                        type=str, 
                        required=True, 
                        metavar='FILEPATH',
                        dest='input_file',
                        help='filepath to the csv file containing the data',
                        action='store')

    parser.add_argument('--x-column', 
                        type=str, 
                        required=True, 
                        metavar='X_COLUMN',
                        dest='x_column',
                        help='name of the x column in the data source',
                        action='store')

    parser.add_argument('--y-column', 
                        type=str, 
                        required=True, 
                        metavar='Y_COLUMN',
                        dest='y_column',
                        help='name of the y column in the data source',
                        action='store')

    parser.add_argument('--z-column', 
                        type=str, 
                        required=True, 
                        metavar='Z_COLUMN',
                        dest='z_column',
                        help='name of the z column in the data source',
                        action='store')

    parser.add_argument('--title', 
                        type=str, 
                        dest='title',
                        metavar='FILEPATH',
                        help='title of the graphic',
                        action='store')

    parser.add_argument('--x-label', 
                        type=str, 
                        metavar='L',
                        dest='x_label',
                        help='label for the x axis',
                        action='store')

    parser.add_argument('--y-label', 
                        type=str, 
                        dest='y_label',
                        metavar='L',
                        help='label for the y axis',
                        action='store')

    parser.add_argument('--output', 
                        type=str, 
                        metavar='FILEPATH',
                        dest='output_file',
                        help='filepath of output file to save the image. If not present, the result will be displayed',
                        action='store')

    parser.add_argument('--x-change', 
                        type=str, 
                        metavar='CODE',
                        dest='x_change',
                        help='transforms the x column using the variables data, i, and x. For example: --x-change "math.log2(data[i,x])"',
                        action='store')

    parser.add_argument('--y-change', 
                        type=str, 
                        metavar='CODE',
                        dest='y_change',
                        help='transforms the y column using the variables data, i, and y. For example: --y-change "math.log2(data[i,y])"',
                        action='store')

    parser.add_argument('--z-change', 
                        type=str, 
                        dest='z_change',
                        metavar='CODE',
                        help='transforms the z column using the variables data, i, and z. For example: --z-change "data[0,0] / data[i,z]"',
                        action='store')

    parser.add_argument('--z-format', 
                        type=str,  
                        metavar='CODE',
                        dest='z_format',
                        help='format displayed z values using the variables data, i, and z. Example: --z-format f"{int(float(data[i,z]))}"',
                        action='store')

    parser.add_argument('--size', 
                        type=float, 
                        nargs=2, 
                        dest='size',
                        metavar='W H',
                        help='size of output image',
                        action='store')

    parser.add_argument('--reduce', 
                        type=str, 
                        choices=('sum', 'mean', 'std', 'product', 'min', 'max'),
                        default='mean',
                        dest='reduce',
                        metavar='FUNC',
                        help='if the x,y pair have multiple values, reduce them using the given function.',
                        action='store')

    parser.add_argument('--verbose', 
                        help='print extra info during execution',
                        action='store_true')

    parser.add_argument('--colormap', 
                        type=str, 
                        dest='colormap',
                        nargs='*',
                        metavar=('NAME|C1', 'C2...'),
                        help='list of HTML colors without # or name of colormap from https://matplotlib.org/stable/tutorials/colors/colormaps.html',
                        action='store')

    return parser.parse_args(args=argv)
