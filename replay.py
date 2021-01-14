import gzip
import json
from typing import List
from enum import Enum, auto

from oraplayexceptions import OraPlayBaseException, __LINE__

class RandomType(Enum):
    Normal = auto()
    Mirror = auto()
    Random = auto()
    Others = auto()

class Replay():
    def __init__(self, path: str):
        with gzip.open(path) as f:
            self.data = json.load(f)
        if self.data["randomoption"] == 0:
            self.option = RandomType.Normal
        elif self.data["randomoption"] == 1:
            self.option = RandomType.Mirror
        elif self.data["randomoption"] == 2:
            self.option = RandomType.Random
        else:
            # 現在未対応
            self.option = RandomType.Others

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def get_keys(self) -> List:
        return self.data["keylog"]

    def get_pattern_modify(self) -> List[int]:
        if self.option == RandomType.Normal:
            return [0, 1, 2, 3, 4, 5, 6]
        if self.option == RandomType.Mirror:
            return [0, 1, 2, 3, 4, 5, 6]
        if self.option == RandomType.Random:
            return self.data["pattern"][0]["modify"]
        if self.option == RandomType.Others:
            raise OraPlayBaseException("this option is not supported", __LINE__)
