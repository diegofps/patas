from patas.utils import expand_path, abort, warn
from glob import glob

import yaml
import csv
import os
import re


class Pattern:
    
    def __init__(self, name, pattern):

        self.name  = "out_" + name
        self.raw   = pattern
        self.data  = None

        self.raw   = self.raw.replace("@float@", "[-0-9\\.e\\+]+")
        self.raw   = self.raw.replace("@int@", "[-0-9\\+]+")
        self.raw   = self.raw.replace("@slug@", "[-0-9a-zA-Z_]+")
        self.raw   = self.raw.replace("@str@", "\"[^\"]+\"")

        self.regex = re.compile(self.raw)
   
    def clear(self):

        self.data = None

    def get_name(self):

        return self.name

    def get_value(self):

        # if self.data is None:
        #     sys.stdout.write("!(" + self.name + ")")
        return self.data

    def value(self):

        return self.data
    
    def check(self, row):

        m:re.Match = self.regex.search(row)

        if m:
            self.data = m.groups()[0]
            return True
        else:
            return False


class TaskParser:

    def __init__(self, experiment_info_filepath, patterns, linebreakers, verbose=False):

        self.linebreakers = linebreakers
        self.patterns = patterns
        self.verbose = verbose
        self.header_names = []
        self.header_map = {}

        # Add input variable columns

        with open(experiment_info_filepath, "r") as fin:
            experiment_info = yaml.load(fin, Loader=yaml.FullLoader)
        
        for var_name in experiment_info["variables"].keys():
            self._add_column("in_" + var_name)

        # Add pattern columns

        for pattern in patterns:
            self._add_column(pattern.name)

        # Add columns with extra info
        
        if verbose:
            for var_name in ["break_id", "task_id", "repeat_id", "combination_id", "experiment_id", "experiment_name", 
                            "duration", "started_at", "ended_at", "tries", "max_tries", 
                            "cluster_id", "cluster_name", "node_id", "node_name", "worker_id", "output_dir", "work_dir"]:

                self._add_column(var_name)

        self.row_values = [None for _ in range(len(self.header_map))]


    def _add_column(self, name):

        if name in self.header_map:
            abort("Header appears multiple times:", name)
        
        self.header_names.append(name)
        self.header_map[name] = len(self.header_map)


    def digest(self, task_folderpath, writer):

        # Filepaths for each task files

        info_filepath   = os.path.join(task_folderpath, "info.yml")
        output_filepath = os.path.join(task_folderpath, "stdout")
        done_filepath   = os.path.join(task_folderpath, ".success")

        # We clean the output row, as we will populate it with the data from the task

        for i in range(len(self.row_values)):
            self.row_values[i] = None

        # If the done file does not exist, it means the task wasnot completed, this is likely a user mistake

        if not os.path.exists(done_filepath):
            warn("Task not completed:", task_folderpath)
        
        # Load the task info

        with open(info_filepath, "r") as fin:
            data = yaml.load(fin, Loader=yaml.FullLoader)
        
        # Load the variable values

        for name, value in data["combination"].items():
            name = "in_" + name
            self.row_values[self.header_map[name]] = value

        # Load the extra data

        break_idd = 0

        if self.verbose:

            self.row_values[self.header_map["break_id"        ]] = str(break_idd)
            self.row_values[self.header_map["task_id"         ]] = data["task_id"         ]
            self.row_values[self.header_map["repeat_id"       ]] = data["repeat_id"       ]
            self.row_values[self.header_map["combination_id"  ]] = data["combination_id"  ]
            self.row_values[self.header_map["experiment_id"   ]] = data["experiment_id"   ]
            self.row_values[self.header_map["experiment_name" ]] = data["experiment_name" ]
            self.row_values[self.header_map["duration"        ]] = data["duration"        ]
            self.row_values[self.header_map["started_at"      ]] = data["started_at"      ]
            self.row_values[self.header_map["ended_at"        ]] = data["ended_at"        ]
            self.row_values[self.header_map["tries"           ]] = data["tries"           ]
            self.row_values[self.header_map["max_tries"       ]] = data["max_tries"       ]
            self.row_values[self.header_map["output_dir"      ]] = data["output_dir"      ]
            self.row_values[self.header_map["work_dir"        ]] = data["work_dir"        ]

            self.row_values[self.header_map["cluster_id"  ]] = data["env_variables"]["PATAS_CLUSTER_ID"  ]
            self.row_values[self.header_map["cluster_name"]] = data["env_variables"]["PATAS_CLUSTER_NAME"]
            self.row_values[self.header_map["node_id"     ]] = data["env_variables"]["PATAS_NODE_ID"     ]
            self.row_values[self.header_map["node_name"   ]] = data["env_variables"]["PATAS_NODE_NAME"   ]
            self.row_values[self.header_map["worker_id"   ]] = data["env_variables"]["PATAS_WORKER_ID"   ]

        # Parse the patterns and write to output

        pattern:Pattern = None

        with open(output_filepath, "r") as fin:
            for line in fin:

                # Check all patterns and capture the desired variables

                for pattern in self.patterns:
                    if pattern.check(line):
                        self.row_values[self.header_map[pattern.get_name()]] = pattern.get_value()
                
                # If line breaks are defined, we will write a row every time one of them is detected and clean the captured patterns so far

                for linebreaker in self.linebreakers:
                    if linebreaker.check(line):

                        writer.writerow(self.row_values)

                        break_idd += 1
                        self.row_values[self.header_map["break_id"]] = str(break_idd)

                        for pattern in self.patterns:
                            self.row_values[self.header_map[pattern.get_name()]] = None
        
        # If we are not using line breakers, we always write the row after all lines were processed

        if not self.linebreakers:
            writer.writerow(self.row_values)


class ExperimentParser:

    def __init__(self, patterns, linebreakers, verbose=False):

        self.linebreakers = linebreakers
        self.patterns     = patterns
        self.verbose      = verbose


    def start(self, experiment_folder, output_file):

        experiment_folder        = expand_path(experiment_folder)
        experiment_info_filepath = os.path.join(experiment_folder, "info.yml")
        task_folderpaths         = glob(os.path.join(experiment_folder, "*"))
        parser                   = TaskParser(experiment_info_filepath, self.patterns, self.linebreakers, self.verbose)
        
        if output_file is None:
            
            experiment_name = os.path.basename(os.path.dirname(experiment_info_filepath))
            output_file     = os.path.join(experiment_folder, experiment_name + ".csv")

        with open(output_file, "w") as fout:

            writer = csv.writer(fout, delimiter=",")
            writer.writerow(parser.header_names)

            for task_folderpath in task_folderpaths:
                if os.path.isdir(task_folderpath):
                    parser.digest(task_folderpath, writer)
