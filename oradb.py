import sqlite3
from enum import Enum, auto

class HashType(Enum):
    md5 = auto()
    sha256 = auto()

class SongDB():
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)

    def get_file_path(self, hash: str, hash_type: HashType=HashType.sha256):
        if hash_type == HashType.sha256:
            hash_str = "sha256"
        elif hash_type == HashType.md5:
            hash_str = "md5"
        c = self.db.execute("SELECT path FROM song WHERE {}='{}'".format(hash_str, hash))
        data = c.fetchone()
        return data[0]
