import argparse


DEFAULT_PATAS_OUTPUT_DIR = './pataslab'
DEFAULT_FIG_SIZE = (10, 7)


def parse_patas_explore(argv):

    # argparse for 'patas explore grid'

    parser = argparse.ArgumentParser(
                        prog='patas explore',
                        description='Start a hyperparameter search.',
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

    parser.add_argument('-q',
                        dest='quiet',
                        help="only display critical events",
                        action='store_true')

    parser.add_argument('-o',
                        type=str,
                        default=DEFAULT_PATAS_OUTPUT_DIR,
                        metavar='FOLDER',
                        dest='output_folder',
                        help="folder to store the program outputs",
                        action='store')

    # Quick Experiment parameters

    parser.add_argument('--type',
                        default='grid',
                        metavar='NAME',
                        choices=('grid', 'cdeepso'),
                        help='type of experiment to execute',
                        action='store')

    parser.add_argument('--redo',
                        dest='redo_tasks',
                        help="forces patas to redo all tasks when an experiment is executed again",
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
                        help="defines an input variable that can assume a fixed number of values, used only in grid search",
                        action='append')

    parser.add_argument('--va',
                        type=str,
                        nargs=4,
                        default=[],
                        metavar=('NAME', 'MIN', 'MAX', 'FACTOR'),
                        dest='var_arithmetic',
                        help="defines an input variable that grows according to an arithmetic progression, used only in grid search",
                        action='append')

    parser.add_argument('--vg',
                        type=str,
                        nargs=4,
                        default=[],
                        metavar=('NAME', 'MIN', 'MAX', 'FACTOR'),
                        dest='var_geometric',
                        help="defines an input variable that grows according to a geometric progression, used only in grid search",
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

    parser.add_argument('--score-pattern',
                        type=str,
                        metavar='REGEX',
                        dest='score_pattern',
                        help="Pattern used to capture the fitness of the particle, used only with CDEEPSO search",
                        action='store')

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
                        description='Draws a heatmap from a csv file',
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

    parser.add_argument('--x-change', 
                        type=str, 
                        metavar='CODE',
                        dest='x_change',
                        help='transforms the x column. For example: --x-change "math.log2(X[i])"',
                        action='store')

    parser.add_argument('--y-change', 
                        type=str, 
                        metavar='CODE',
                        dest='y_change',
                        help='transforms the y column. For example: --y-change "math.log2(Y[i])"',
                        action='store')

    parser.add_argument('--z-change', 
                        type=str, 
                        dest='z_change',
                        metavar='CODE',
                        help='transforms the z column. For example: --z-change "Z[0]/Z[i]"',
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

    parser.add_argument('--z-label', 
                        type=str, 
                        dest='z_label',
                        metavar='L',
                        help='label for the colorbar',
                        action='store')

    parser.add_argument('--output', 
                        type=str, 
                        default=None,
                        metavar='FILEPATH',
                        dest='output_file',
                        help='filepath of output file to save the image. If not present, the result will be displayed',
                        action='store')

    parser.add_argument('--aggfunc', 
                        type=str, 
                        choices=('sum', 'mean', 'std', 'product', 'min', 'max', 'count'),
                        default='mean',
                        dest='aggfunc',
                        metavar='NAME',
                        help='aggregation function to use when x,y coordinates map to multiple values.',
                        action='store')

    parser.add_argument('--fmt', 
                        type=str,  
                        metavar='CODE',
                        dest='fmt',
                        default='.2f',
                        help='string used to format annotations',
                        action='store')

    parser.add_argument('--fig-size', 
                        type=float, 
                        nargs=2, 
                        dest='fig_size',
                        metavar='W H',
                        default=DEFAULT_FIG_SIZE,
                        help='size of output image',
                        action='store')

    parser.add_argument('--annot', 
                        help='Enable cell annotation',
                        default=False,
                        action='store_true')

    # parser.add_argument('--colormap', 
    #                     type=str, 
    #                     dest='colormap',
    #                     nargs='*',
    #                     metavar=('NAME|C1', 'C2...'),
    #                     help='list of HTML colors without # or name of colormap from https://matplotlib.org/stable/tutorials/colors/colormaps.html',
    #                     action='store')

    return parser.parse_args(args=argv)


def parse_patas_draw_bars(argv):

    parser = argparse.ArgumentParser(
                        prog='patas draw bars',
                        description='Draws bars from a csv file',
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

    parser.add_argument('--r-label', 
                        type=str, 
                        dest='r_label',
                        metavar='L',
                        help='label for the reduced values',
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
                        help='transforms the x column using the variables X, Y, Z, math, and i. For example: --x-change "math.log2(X[i])"',
                        action='store')

    parser.add_argument('--y-change', 
                        type=str, 
                        metavar='CODE',
                        dest='y_change',
                        help='transforms the y column using the variables X, Y, Z, math, and i. For example: --y-change "math.log2(Y[i])"',
                        action='store')

    parser.add_argument('--r-function', 
                        type=str, 
                        choices=('sum', 'mean', 'std', 'product', 'min', 'max'),
                        default='mean',
                        dest='r_function',
                        metavar='NAME',
                        help='each x value will usualy map to multiple values, this function defines how to reduce them.',
                        action='store')

    parser.add_argument('--r-format', 
                        type=str,  
                        metavar='CODE',
                        dest='r_format',
                        help='formats reduced values for display. Example: --r-format \'int(D[x]*100)\'',
                        action='store')

    parser.add_argument('--size', 
                        type=float, 
                        nargs=2, 
                        dest='size',
                        metavar='W H',
                        help='size of output image',
                        action='store')

    parser.add_argument('--verbose', 
                        help='print extra info during execution',
                        action='store_true')

    parser.add_argument('--bar-color', 
                        type=str, 
                        dest='bar_color',
                        metavar='COLOR',
                        help='an HTML color without #',
                        action='store')

    parser.add_argument('--bar-size', 
                        type=float, 
                        dest='bar_size',
                        metavar='W',
                        help='size of each bar, a value from 0.0 to 1.0',
                        action='store')

    parser.add_argument('--border', 
                        type=str,
                        choices=('all', 'ticks', 'lines', 'none'),
                        dest='border',
                        metavar='MODE',
                        help='style of the border, default is all',
                        action='store')

    parser.add_argument('--ticks', 
                        type=int, 
                        dest='ticks',
                        metavar='T',
                        help='number of values to appear in the axis',
                        action='store')

    parser.add_argument('--ticks-format', 
                        type=str,  
                        metavar='CODE',
                        dest='ticks_format',
                        help='formats tick display value using its current value t. Example: --ticks-format \'t:02f\'',
                        action='store')

    parser.add_argument('--horizontal',  
                        dest='horizontal',
                        help='set this flag if you want horizontal bars',
                        action='store_true')

    parser.add_argument('--show-grid',  
                        dest='show_grid',
                        help='set this flag if you want gridlines displayed',
                        action='store_true')

    parser.add_argument('--show-error',  
                        dest='show_error',
                        help='set this flag if you want the standard deviation to be shown',
                        action='store_true')

    return parser.parse_args(args=argv)


def parse_patas_draw_lines(argv):

    parser = ArgumentParser2(
                        prog='patas draw lines',
                        description='Draws lines from a csv file',
                        epilog="Check the README.md to learn more tips on how to use this feature: https://github.com/diegofps/patas/blob/main/README.md",
                        formatter_class=argparse.RawDescriptionHelpFormatter)


    # GENERAL PARAMETERS

    parser.add_argument('--input', 
                        type=str, 
                        required=True, 
                        metavar='FILEPATH',
                        dest='input_file',
                        help='filepath to the csv file containing the data',
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

    parser.add_argument('--r-label', 
                        type=str, 
                        dest='r_label',
                        metavar='L',
                        help='label for the reduced values',
                        action='store')

    parser.add_argument('--output', 
                        type=str, 
                        metavar='FILEPATH',
                        dest='output_file',
                        help='filepath of output file to save the image. If not present, the result will be displayed',
                        action='store')

    parser.add_argument('--size', 
                        type=float, 
                        nargs=2, 
                        dest='size',
                        metavar='W H',
                        help='size of output image',
                        action='store')

    parser.add_argument('--verbose', 
                        help='print extra info during execution',
                        action='store_true')

    parser.add_argument('--border', 
                        type=str,
                        choices=('all', 'ticks', 'lines', 'none'),
                        dest='border',
                        metavar='MODE',
                        help='style of the border, default is all',
                        action='store')

    parser.add_argument('--ticks', 
                        type=int, 
                        dest='ticks',
                        metavar='T',
                        help='number of values to appear in the axis',
                        action='store')

    parser.add_argument('--ticks-format', 
                        type=str,  
                        metavar='CODE',
                        dest='ticks_format',
                        help='formats tick display value using its current value t. Example: --ticks-format \'t:02f\'',
                        action='store')

    parser.add_argument('--legend-location', 
                        type=str, 
                        choices=('tr', 'tl', 'bl', 'br', 'cr', 'cl', 'tc', 'bc', 'cc', 'c'),
                        default=None,
                        dest='legend_location',
                        metavar='YX',
                        help='Position of the legend (t=top, b=bottom, c=center, r=right, l=left)',
                        action='store')

    parser.add_argument('--show-grid', 
                        dest='show_grid', 
                        help='set this flag if you want gridlines displayed', 
                        action='store_true')

    parser.add_argument('--show-error',  
                        dest='show_error',
                        help='set this flag if you want the standard deviation to be shown',
                        action='store_true')


    # LINE PARAMETERS

    parser.add_argument_group('Line parameters')

    lines = parser.add_argument('--new-line', 
                                dest='lines',
                                help='begin definition of a new line',
                                action='create_context')

    parser.add_argument('--x-column', 
                        type=str, 
                        dest='x_column',
                        metavar='X_COLUMN',
                        help='name of the x column in the data source',
                        action='store',
                        context=lines)

    parser.add_argument('--y-column', 
                        type=str, 
                        metavar='Y_COLUMN',
                        dest='y_column',
                        help='name of the y column in the data source',
                        action='store',
                        context=lines)

    parser.add_argument('--x-change', 
                        type=str, 
                        metavar='CODE',
                        dest='x_change',
                        default=None,
                        help='transforms the x column. For example: --x-change "math.log2(X[i])"',
                        action='store',
                        context=lines)

    parser.add_argument('--y-change', 
                        type=str, 
                        metavar='CODE',
                        dest='y_change',
                        help='transforms the y column. For example: --y-change "math.log2(Y[i])"',
                        action='store',
                        context=lines)

    parser.add_argument('--r-function', 
                        type=str, 
                        choices=('sum', 'mean', 'std', 'product', 'min', 'max'),
                        default='mean',
                        dest='r_function',
                        metavar='NAME',
                        help='each x value will usualy map to multiple values, this function defines how to reduce them.',
                        action='store',
                        context=lines)

    parser.add_argument('--label', 
                        type=str, 
                        dest='label',
                        metavar='NAME',
                        help='label representing this line in the legend',
                        action='store',
                        context=lines)

    parser.add_argument('--style', 
                        type=str, 
                        choices=('solid', 'dash', 'dashdot', 'dot'),
                        default=None,
                        dest='style',
                        metavar='NAME',
                        help='style used to draw the line',
                        action='store',
                        context=lines)

    parser.add_argument('--marker', 
                        type=str, 
                        choices=('point', 'circle', 'x', 'diamond', 'hexagon', 'square', 'plus'),
                        default=None,
                        dest='marker',
                        metavar='NAME',
                        help='marker used to highlight the points in the line',
                        action='store',
                        context=lines)

    parser.add_argument('--marker-size', 
                        type=float, 
                        default=5,
                        dest='marker_size',
                        metavar='FLOAT',
                        help='size of the marker',
                        action='store',
                        context=lines)



    args = parser.parse_args(args=argv)

    print(args)
    
    return args


class ArgumentParser2(argparse.ArgumentParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dest_to_context = {}
        self.queues = {}

    def add_argument(self, *args, **params):
        if 'context' in params:
            context = params.pop('context')
            action = super().add_argument(*args, **params)
            context.intercept(action)
            return action
        
        elif 'action' in params and params['action'] == 'create_context':
            context = ArgContextClass(self)
            params['action'] = context
            action = super().add_argument(*args, **params)
            self.dest_to_context[action.dest] = context
            return context
        
        else:
            return super().add_argument(*args, **params)

    def parse_args(self, *args, **kwargs):
        args = super().parse_args(*args, **kwargs)
        for dest, context in self.dest_to_context.items():
            args.__dict__[dest] = context.instances
        return args


class ArgContextInstance(argparse.Namespace):
    def __init__(self):
        super().__init__()


class ArgContextClass:

    def __init__(self, parser):
        self._instances = []
        self._intercepting = []
        self._parser = parser
    
    def any(self):
        return any(self._instances)
    
    @property
    def instance(self):
        if not self._instances:
            self.create_instance()
        return self._instances[-1]
    
    @property
    def instances(self):
        return self._instances
    
    def create_instance(self):
        instance = ArgContextInstance()
        self._instances.append(instance)

        for action in self._intercepting:
            instance.__dict__[action.dest] = action.default

    def intercept(self, action):
        
        context_class = self
        def _custom_call(self, parser, namespace, values, option_string=None, **kwargs):
            if hasattr(self.__class__, '__old_call__'):
                method = getattr(self.__class__, '__old_call__')
                method(self, parser, context_class.instance, values, option_string=None, **kwargs)
                
        if not hasattr(action.__class__, '__old_call__'):
            old_call = getattr(action.__class__, '__call__')
            setattr(action.__class__, '__old_call__', old_call)
            setattr(action.__class__, '__call__', ArgContextClass._class_call)
            
        if not hasattr(action, '__custom_call__'):
            setattr(action, '__custom_call__', _custom_call)
        
        self._intercepting.append(action)
            
    def __call__(self, *args, **kwargs):
        return ArgContextClass._Stepper(self, *args, **kwargs)

    class _Stepper(argparse.Action):
        def __init__(self, context, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context:ArgContextClass = context
            self.nargs = 0
        
        def __call__(self, *args, **kwargs):
            if self.context.any():
                self.context.create_instance()
            return self
    
    @staticmethod
    def _class_call(self, parser, namespace, values, option_string=None, **kwargs):
        if hasattr(self, '__custom_call__'):
            method = getattr(self, '__custom_call__')
            method(self, parser, namespace, values, option_string, **kwargs)
        
        elif hasattr(self.__class__, '__old_call__'):
            method = getattr(self.__class__, '__old_call__')
            method(self, parser, namespace, values, option_string, **kwargs)
