import os
import json
from datetime import datetime, timedelta

class SDB():
    '''Session Database'''

    def __init__(self, session_id, owner=False) -> None:
        self.session_id = session_id
        self.file_path = SDB._get_file_path(self.session_id)
        self.owner = owner

        if owner is True:
            self._create_file()
        else:
            assert os.path.exists(self.file_path), "Cannot find the path of SDB file for a client SDB instance."


    @staticmethod
    def _get_file_path(session_id):

        # The internal/ directory path where sdb files are stored
        fname_prefix = 'sdb_'
        fname_suffix = 'json'
        internal_dir =  os.path.join(
            os.path.dirname(__file__),
            '..',
            'internal'
        )
        assert os.path.isdir(internal_dir), "Couldn't find internal/ directory in visualCaseGen"

        # File path for the given session id
        file_path = os.path.join(internal_dir, f'{fname_prefix}{session_id}.{fname_suffix}')
        return file_path

    def get_data(self):
        assert os.path.exists(self.file_path), "Cannot find the path of SDB file while attempting to read data."
        f = open(self.file_path)    # file obj
        d = json.load(f)            # dict obj containing info from json file
        f.close()
        return d


    def _create_file(self):

        assert not os.path.exists(self.file_path), "SDB file already exists"  

        # stat dict to be written to json file
        date_str = datetime.today().strftime('%Y-%m-%d_%H:%M:%S')

        d = {'created': date_str}

        # write json file
        with open(self.file_path, 'w') as f:
            json.dump(d, f)
    

    def append(self, d_new):

        # first read the original data
        d = self.get_data()

        # now update data
        d.update(d_new)

        # finally, write to previous file
        f = open(self.file_path, 'w')    # file obj
        json.dump(d, f)
        f.close()
    
    def query_variable(self, var):
        d = self.get_data()
        return d.get(var)

    def remove_file(self):
        assert self.owner is True, "An SDB file can be removed by an owner SDB instance only."
        os.remove(self.file_path)

