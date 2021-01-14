import sqlite3

class SongDB():
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)

    def get_file_path(self, sha256: str):
        c = self.db.execute("SELECT path FROM song WHERE sha256='{}'".format(sha256))
        data = c.fetchone()
        return data[0]
