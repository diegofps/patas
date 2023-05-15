from .utils import error

import yaml


def format_as_dict(obj):

    if isinstance(obj, Schema):
        obj = obj.__dict__
    
    if isinstance(obj, list):
        return [format_as_dict(x) for x in obj]

    if isinstance(obj, tuple):
        return (format_as_dict(x) for x in obj)
    
    if isinstance(obj, dict):
        return { k:format_as_dict(v) for k,v in obj.items() if not k.startswith('_') }

    return obj


class Schema:

    def load_property(self, name, data, mandatory=False):
        
        if name in data:
            setattr(self, name, data[name])
        
        elif mandatory:
            error(f"Missing required property in {self.__class__.__name__}: {name}")


class NodeSchema(Schema):

    def __init__(self, data=None):
        
        self.tags = []
        self.hostname = ""
        self.workers = 1
        self.user = None
        self.port = 22
        self.name = 'noname'
        self.private_key = None
        self._credential = None

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
        
        self.name = "default"
        self.nodes = []

        if data is not None:
            self.init_from(data)

    def init_from(self, data):

        self.load_property('name', data)
        self.load_property('nodes', data, mandatory=True)
        
        self.nodes = [NodeSchema(x) for x in self.nodes]

        return self


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

        self.type = 'arithmetic'
        self.name = None
        self.values = []
        self.step = 1
        self.min  = 0
        self.max  = 10

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

        self.type = 'geometric'
        self.name = None
        self.values = []
        self.factor = 2
        self.min = 1
        self.max = 17

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
        
        self.name      = None
        self.workdir   = None
        self.cmd       = []
        self.max_tries = 3
        self.repeat    = 1

    def init_from(self, data):
        
        self.load_property('name', data)
        self.load_property('workdir', data)
        self.load_property('cmd', data, mandatory=True)
        self.load_property('max_tries', data)
        self.load_property('repeat', data)

        if not isinstance(self.cmd, list):
            self.cmd = [self.cmd]
        
        return self
        

class GridExperimentSchema(Schema):

    def __init__(self):
        
        super().__init__()
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


class CDEEPSOExperimentSchema(BaseExperimentSchema):

    def __init__(self):
        
        super().__init__()
        self.score = None
    
    def init_from(self, data):

        super().init_from(data)
        self.load_property('score', data, mandatory=True)
        return self


def load_cluster(filepath):
    with open(filepath, "r") as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
        return ClusterSchema().init_from(data)


def load_experiment(filepath):
    with open(filepath, "r") as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
        return GridExperimentSchema().init_from(data)


def save_cluster(filepath:str, data:ClusterSchema):
    with open(filepath, "w") as fout:
        yaml.dump(format_as_dict(data), fout, default_flow_style=False)


def save_experiment(filepath:str, data:ClusterSchema):
    with open(filepath, "w") as fout:
        yaml.dump(format_as_dict(data), fout, default_flow_style=False)


def format_as_yaml(data:Schema):
    return yaml.dump(format_as_dict(data), default_flow_style=False)

