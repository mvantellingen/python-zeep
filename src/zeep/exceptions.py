
class TransportError(IOError):
    pass


class Fault(IOError):
    def __init__(self, message, code=None, actor=None, detail=None):
        super(Fault, self).__init__(message)
        self.message = message
        self.code = code
        self.actor = actor
        self.detail = detail
