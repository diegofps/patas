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
            error("Missing mandatory property in Node schema: " + name)


class Node(Schema):

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


class Cluster(Schema):

    def __init__(self, data=None):
        
        self.name = "default"
        self.nodes = []

        if data is not None:
            self.init_from(data)

    def init_from(self, data):

        self.load_property('name', data)
        self.load_property('nodes', data, mandatory=True)
        
        self.nodes = [Node(x) for x in self.nodes]

        return self


class ListVariable(Schema):
    
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


class ArithmeticVariable(Schema):
    
    def __init__(self, data=None):

        self.type = 'arithmetic'
        self.name = None
        self.factor = 1
        self.min = 0
        self.max = 10

        if data is not None:
            self.init_from(data)

        self.update()
    
    def update(self):
        self._values = self.arange(self.first, self.last, self.step)
    
    @property
    def values(self):
        return self._values
    
    def init_from(self, data):

        self.load_property('factor', data)
        self.load_property('name', data)
        self.load_property('min', data)
        self.load_property('max', data)

        return self


class GeometricVariable(Schema):
    
    def __init__(self, data=None):

        self.type = 'geometric'
        self.name = None
        self.factor = 2
        self.min = 1
        self.max = 17

        if data is not None:
            self.init_from(data)
    
        self.update()
    
    def update(self):
        self._values = list()
        current = self.first
        
        while current < self.last:
            self._values.append(current)
            current = current * self.factor
    
    @property
    def values(self):
        return self._values
    
    def init_from(self, data):

        self.load_property('factor', data)
        self.load_property('name', data)
        self.load_property('min', data)
        self.load_property('max', data)

        return self


class Experiment(Schema):

    def __init__(self):
        self.cmd = []
        self.name = None
        self.workdir = None
        self.repeat = 1
        self.max_tries = 3
        self.vars = []
    
    def init_from(self, data):

        self.load_property('name', data)
        self.load_property('workdir', data)
        self.load_property('repeat', data)
        self.load_property('max_tries', data)
        self.load_property('cmd', data, mandatory=True)

        if not isinstance(self.cmd, list):
            self.cmd = [self.cmd]
        
        if 'vars' in data:
            self.vars = []

            for data2 in data['vars']:

                if 'type' in data2:
                    if data2['type'] == 'list':
                        self.vars.append(ListVariable(data2))

                    elif data2['type'] == 'arithmetic':
                        self.vars.append(ArithmeticVariable(data2))

                    elif data2['type'] == 'geometric':
                        self.vars.append(GeometricVariable(data2))

                    else:
                        error(f"Invalid property value in Variable Schema: type={data2['type']}")
                else:
                    error('Missing mandatory property in Variable Schema: type')

        return self


def load_cluster(filepath):
    with open(filepath, "r") as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
        return Cluster().init_from(data)


def load_experiment(filepath):
    with open(filepath, "r") as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
        return Experiment().init_from(data)


def save_cluster(filepath:str, data:Cluster):
    with open(filepath, "w") as fout:
        yaml.dump(format_as_dict(data), fout, default_flow_style=False)


def save_experiment(filepath:str, data:Cluster):
    with open(filepath, "w") as fout:
        yaml.dump(format_as_dict(data), fout, default_flow_style=False)


def format_as_yaml(data:Schema):
    return yaml.dump(format_as_dict(data), default_flow_style=False)

