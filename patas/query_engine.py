from patas.utils import quote_single, run, abort

from glob import glob

import os


class QueryEngine:

    def __init__(self, patas_folder):
        
        self.tables = []

        for folderpath in glob(os.path.join(patas_folder, '*')):
            if os.path.isdir(folderpath):
                experiment_name = os.path.basename(folderpath)
                table_filepath = os.path.join(folderpath, experiment_name + '.csv')
                if os.path.exists(table_filepath):
                    self.tables.append(f'"{table_filepath}"')

    def query(self, query, pretty_print):
        

        tables = " ".join(self.tables)

        if pretty_print:
            cmd = f"csvsql -d ',' --query {quote_single(query)} {tables} 2> /dev/null | csvlook"
        else:
            cmd = f"csvsql -d ',' --query {quote_single(query)} {tables} 2> /dev/null"
        
        status, _ = run(cmd)

        if status != 0:
            abort("Could not call csvkit, is it accessible in $PATH?")
        

