from .utils import error, warn, abort, clean_folder
from functools import reduce

import hashlib
import base64
import yaml
import copy
import os


def format_as_dict(obj):

    if isinstance(obj, Schema):
        obj = obj.__dict__
    
    if isinstance(obj, list):
        return [format_as_dict(x) for x in obj]

    if isinstance(obj, tuple):
        return (format_as_dict(x) for x in obj)
    
    if isinstance(obj, dict):
        return {k:format_as_dict(v) for k,v in obj.items() if not k.startswith('_')}

    return obj


class Schema:

    def load_property(self, name, data, mandatory=False):
        
        if name in data:
            setattr(self, name, data[name])
        
        elif mandatory:
            error(f"Missing required property in {self.__class__.__name__}: {name}")


class Task:

    def __init__(self, 
            experiment_name, task_output_dir, work_dir, experiment_idd, combination_idd, 
            repeat_idd, task_idd, combination, cmdlines, max_tries):

        self.experiment_name = experiment_name
        self.output_dir      = task_output_dir
        self.combination_idd = combination_idd
        self.experiment_idd  = experiment_idd
        self.combination     = combination
        self.repeat_idd      = repeat_idd
        self.max_tries       = max_tries
        self.work_dir        = work_dir
        self.task_idd        = task_idd
        self.commands        = cmdlines
        self.assigned_to     = None
        self.success         = None
        self.attempts        = []
        self.tries           = 0
    
    def __repr__(self):

        combination = ";".join(f"{k}={v}" for k, v in self.combination.items())
        return f"{self.experiment_idd} {self.combination_idd} {self.repeat_idd} {self.task_idd} {combination} {self.commands}"


class NodeSchema(Schema):

    def __init__(self, data=None):
        
        self.cluster_idd = None
        self.global_idd  = None

        self.name        = 'noname'
        self.private_key = None
        self._credential = None
        self.user        = None
        self.tags        = []
        self.hostname    = ""
        self.port        = 22
        self.workers     = 1

        if data is not None:
            self.init_from(data)

    def init_from(self, data):

        self.load_property('hostname', data, mandatory=True)
        self.load_property('workers', data)
        self.load_property('tags', data)
        self.load_property('user', data)
        self.load_property('port', data)
        self.load_property('name', data)

        return self

    @property
    def credential(self):
        
        if self._credential is None:
        
            if self.user is None:
                self._credential = self.ip
        
            else:
                self._credential = self.user + "@" + self.ip

        return self._credential
    
    @property
    def ip(self):
        
        return self.hostname


class ClusterSchema(Schema):

    def __init__(self, data=None):
        
        self.global_idd = None
        self.name = "default"
        self.nodes = []

        if data is not None:
            self.init_from(data)

    def init_from(self, data):

        self.load_property('name', data)
        self.load_property('nodes', data, mandatory=True)
        
        self.nodes = [NodeSchema(x) for x in self.nodes]

        return self

    def number_of_nodes(self):
        return len(self.nodes)

    def number_of_workers(self):
        return reduce(lambda a,b:a+b.workers, self.nodes, 0)

    def show_summary(self, indent=4):

        lines = [f"'{self.name}' has {self.number_of_nodes()} node(s):"] + \
                [f"    '{node.name}' has {node.workers} worker(s)" for node in self.nodes]
        
        data = ' ' * indent + ('\n' + ' ' * indent).join(lines)
        print(data)
    

class ListVariableSchema(Schema):
    
    def __init__(self, data=None):

        self.type = 'list'
        self.name = None
        self.values = []

        if data is not None:
            self.init_from(data)
    
    def init_from(self, data):

        self.load_property('values', data, mandatory=True)
        self.load_property('name', data)
        self.load_property('type', data)

        return self


class ArithmeticVariableSchema(Schema):
    
    def __init__(self, data=None):

        self.type   = 'arithmetic'
        self.name   = None
        self.values = []
        self.step   = 1
        self.min    = 0
        self.max    = 10

        if data is not None:
            self.init_from(data)

        self.update()
    
    def update(self):
        from numpy import arange
        self.values = arange(self.min, self.max, self.step).tolist()
    
    def init_from(self, data):

        self.load_property('step', data)
        self.load_property('name', data)
        self.load_property('min', data)
        self.load_property('max', data)

        return self


class GeometricVariableSchema(Schema):
    
    def __init__(self, data=None):

        self.type   = 'geometric'
        self.name   = None
        self.values = []
        self.factor = 2
        self.min    = 1
        self.max    = 17

        if data is not None:
            self.init_from(data)
    
        self.update()
    
    def update(self):
        
        self.values = list()
        current = self.first
        
        while current < self.last:
            self.values.append(current)
            current = current * self.factor
    
    def init_from(self, data):

        self.load_property('factor', data)
        self.load_property('name', data)
        self.load_property('min', data)
        self.load_property('max', data)

        return self


class BaseExperimentSchema(Schema):

    def __init__(self):
        
        self.type           = 'base'
        self.redo_tasks     = False
        self.name           = None
        self.workdir        = None
        self.task_filters   = []
        self.experiment_idd = None
        self.cmd            = []
        self.max_tries      = 3
        self.repeat         = 1

    def init_from(self, data):
        
        self.load_property('name', data)
        self.load_property('workdir', data)
        self.load_property('cmd', data, mandatory=True)
        self.load_property('max_tries', data)
        self.load_property('repeat', data)
        self.load_property('redo_tasks', data)

        # TODO: Load task filters

        if not isinstance(self.cmd, list):
            self.cmd = [self.cmd]
        
        return self

    def number_of_tasks(self):
        raise NotImplementedError()
        
    def show_summary(self):
        raise NotImplementedError()

    def check_signature(self, output_folder):
        raise NotImplementedError()

    def write_info(self):
        raise NotImplementedError()

    def clean_output(self):
        raise NotImplementedError()

    def on_start(self, scheduler):
        raise NotImplementedError()

    def on_task_completed(self, scheduler, task:Task):
        raise NotImplementedError()

    def on_finish(self):
        raise NotImplementedError()


class GridExperimentSchema(BaseExperimentSchema):

    def __init__(self):
        
        super().__init__()
        self.type = 'grid'
        self.vars = []
    
    def init_from(self, data):

        super().init_from(data)

        if 'vars' in data:
            self.vars = []

            for data2 in data['vars']:

                if 'type' in data2:
                    if data2['type'] == 'list':
                        self.vars.append(ListVariableSchema(data2))

                    elif data2['type'] == 'arithmetic':
                        self.vars.append(ArithmeticVariableSchema(data2))

                    elif data2['type'] == 'geometric':
                        self.vars.append(GeometricVariableSchema(data2))

                    else:
                        error(f"Invalid property value in {self.__class__.__name__}: type={data2['type']}")
                else:
                    error(f'Missing required property in {self.__class__.__name__}: type')

        return self

    def number_of_tasks(self):
        
        return reduce(lambda a,b: a*len(b.values), self.vars, 1) * self.repeat
    
    def show_summary(self, indent=4):

        combinations = reduce(lambda a,b: a*len(b.values), self.vars, 1)
        tasks = combinations * self.repeat
        filters = len(self.task_filters)

        attrs = ['experiment_idd', 'redo_tasks', 'workdir', 'task_filters', 'cmd', 'max_tries', 'repeat']

        lines = [f"'{self.name}' has {len(self.vars)} variable(s), {combinations} combination(s), {tasks} task(s), and {filters} task-filter(s):"] + \
                [f"    {name}: {getattr(self, name)}" for name in attrs] + \
                [ '    Variables:'] + \
                [f"        {v.name} = {str(v.values)}, len = {len(v.values)}" for v in self.vars]
        
        data = ' ' * indent + ('\n' + ' ' * indent).join(lines)
        print(data)

    def _combinations(self, variables, combination={}):

        if len(variables) == len(combination):
            yield copy.copy(combination)
        
        else:
            var  = variables[len(combination)]
            name = var.name
            
            for value in var.values:
                combination[name] = value
                
                for output in self._combinations(variables, combination):
                    yield output
                
            del combination[name]

    def check_signature(self, output_folder):
        
        # Define filepaths

        self.output_folder = os.path.join(output_folder, self.name)
        self.info_filepath = os.path.join(self.output_folder, "info.yml")

        # Data to identify the signature

        signature_data = {
            "type"      : self.type,
            "commands"  : self.cmd,
            "variables" : {v.name:v.values for v in self.vars},
            "workdir"   : self.workdir,
            "repeat"    : self.repeat
        }

        # Calculate signature
        
        key = hashlib.md5()
        key.update(str(format_as_dict(signature_data)).encode())
        signature = base64.b64encode(key.digest()).decode("utf-8")

        # Data to represent the experiment

        self.info = {
            'name': self.name,
            "type": self.type,
            "commands": self.cmd,
            "variables": {v.name:v.values for v in self.vars},
            "workdir": self.workdir,
            'task_filters': self.task_filters,
            'signature': signature,
            'commands': self.cmd,
            'max_tries': self.max_tries,
            'repeat': self.repeat,
            'redo_tasks': self.redo_tasks,
        }

        # Load previous signature, if it exists

        try:
            with open(self.info_filepath, "r") as fin:
                other = yaml.load(fin, Loader=yaml.FullLoader)
        except:
            other = None

        # Return true if the signature do not exist or if they are the same

        return not other or 'signature' not in other or other["signature"] == signature

    def write_info(self):
        
        os.makedirs(self.output_folder, exist_ok=True)

        with open(self.info_filepath, "w") as fout:
            yaml.dump(self.info, fout, default_flow_style=False)

    def clean_output(self):

        clean_folder(self.output_folder)

    def on_start(self, scheduler):
        
        combination_idd = -1
        task_idd        = -1

        for combination in self._combinations(self.vars):
            combination_idd += 1

            for repeat_idd in range(self.repeat):
                task_idd += 1

                task_output_folder = os.path.join(self.output_folder, str(task_idd))

                cmds = [x.format(**combination) for x in self.cmd]

                task = Task(self.name, task_output_folder, self.workdir, self.experiment_idd, combination_idd, repeat_idd, task_idd, combination, cmds, self.max_tries)

                if self.task_filters and not any(a <= task_idd < b for a, b in self.task_filters):
                    scheduler.push_filtered(task)

                elif not self.redo_tasks and os.path.exists(os.path.join(task_output_folder, ".success")):
                    scheduler.push_done(task)

                else:
                    scheduler.push_todo(task)

    def on_task_completed(self, scheduler, task:Task):

        # Define filepaths

        success_filepath = os.path.join(task.output_dir, ".success")
        failure_filepath = os.path.join(task.output_dir, ".failure")
        info_filepath    = os.path.join(task.output_dir, "info.yml")
                
        # Create the task folder

        os.makedirs(task.output_dir, exist_ok=True)
        
        # Clean anything inside the task folder

        clean_folder(task.output_dir, quiet=True)

        # Dump task info
        
        info = {
            "task_id"        : task.task_idd        ,
            "repeat_id"      : task.repeat_idd      ,
            "experiment_id"  : task.experiment_idd  ,
            "experiment_name": task.experiment_name ,
            "combination_id" : task.combination_idd ,
            "combination"    : task.combination     ,
            "max_tries"      : task.max_tries       ,
            "tries"          : task.tries           ,
            "results"        : []                   ,
            "output_dir"     : task.output_dir      ,
            "work_dir"       : task.work_dir        ,
            "commands"       : task.commands        ,
            "success"        : task.success         ,
            "assigned_to"    : task.assigned_to     ,
        }

        for attempt in task.attempts:
            attempt = copy.copy(attempt)
            del attempt['stdout']
            info['results'].append(attempt)
        
        with open(info_filepath, "w") as fout:
            yaml.dump(info, fout, default_flow_style=False)
        
        # Dump fail and success outputs

        for i, attempt in enumerate(task.attempts):
            attempt = task.attempts[i]

            if attempt['status'] == 0:
                filepath = os.path.join(task.output_dir, f'success.stdout')
            else:
                filepath = os.path.join(task.output_dir, f'fail{i}.stdout')
            
            with open(filepath, "wb") as fout:
                fout.write(attempt['stdout'])
        
        # Create .success or .failure file

        filepath = success_filepath if task.success else failure_filepath
        
        with open(filepath, 'a'):
            os.utime(filepath, None)

    def on_finish(self):
        pass


class CDEEPSOExperimentSchema(BaseExperimentSchema):

    def __init__(self):
        
        super().__init__()
        self.score_pattern = None
        self.type = 'cdeepso'
    
    def init_from(self, data):

        super().init_from(data)
        self.load_property('score_pattern', data, mandatory=True)
        return self


def load_cluster(filepath):
    with open(filepath, "r") as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
        return ClusterSchema().init_from(data)


def load_experiment(filepath):
    with open(filepath, "r") as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
        if not 'type' in data:
            data['type'] = 'grid'
        if data['type'] == 'grid':
            return GridExperimentSchema().init_from(data)
        elif data['type'] == 'cdeepso':
            return CDEEPSOExperimentSchema().init_from(data)
        else:
            abort(f'Invalid experiment type: {data["type"]}')


def save_cluster(filepath:str, data:ClusterSchema):
    with open(filepath, "w") as fout:
        yaml.dump(format_as_dict(data), fout, default_flow_style=False)


def save_experiment(filepath:str, data:ClusterSchema):
    with open(filepath, "w") as fout:
        yaml.dump(format_as_dict(data), fout, default_flow_style=False)


def format_as_yaml(data:Schema):
    return yaml.dump(format_as_dict(data), default_flow_style=False)

