import sys

def __LINE__():
    return sys._getframe(1).f_lineno

class OraPlayBaseException(Exception):
    """
    base exception class for oraplay.
    """
    def __init__(self, name: str, message: str, line: int=0):
        self.name = name
        self.message = message
        self.line = line

    def __str__(self):
        return "{} : {} : L.{}".format(self.name, self.message, self.line)

class UnsupportedType(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(self.__name__, message, line)

class InvalidFormat(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(self.__name__, message, line)

class FailedParseReplay(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(self.__name__, message, line)
