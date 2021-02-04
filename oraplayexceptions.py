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

class ArgumentError(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(type(self).__name__, message, line)

    def __str__(self):
        return super(OraPlayBaseException, self).__str__()

class UnsupportedType(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(type(self).__name__, message, line)

    def __str__(self):
        return super(OraPlayBaseException, self).__str__()

class InvalidFormat(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(type(self).__name__, message, line)

    def __str__(self):
        return super(OraPlayBaseException, self).__str__()

class FailedParseReplay(OraPlayBaseException):
    def __init__(self, message: str, line: int=0):
        super(OraPlayBaseException, self).__init__(type(self).__name__, message, line)

    def __str__(self):
        return super(OraPlayBaseException, self).__str__()
