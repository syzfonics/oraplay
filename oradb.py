import sqlite3
from enum import Enum, auto

from bms import BMS
from oraplayexceptions import ArgumentError, __LINE__

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
        else:
            raise ArgumentError("hash type is invalid", __LINE__())
        c = self.db.execute("SELECT path FROM song WHERE {}='{}'".format(hash_str, hash))
        data = c.fetchone()
        return data[0]

    def get_bms_from_hash(self, hash: str, hash_type: HashType=HashType.sha256):
        file_path = self.get_file_path(hash, hash_type)
        return BMS(file_path)
