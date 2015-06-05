class LeanRTMBaseException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class InvalidArgumentException(LeanRTMBaseException): pass
class AppNotFoundOrDisabledException(LeanRTMBaseException): pass
class AppAccessDisabledException(LeanRTMBaseException): pass
