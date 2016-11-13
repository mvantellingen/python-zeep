class Error(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)
        self.message = message

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.message)


class XMLSyntaxError(Error):
    pass


class XMLParseError(Error):
    pass


class UnexpectedElementError(Error):
    pass


class WsdlSyntaxError(Error):
    pass


class TransportError(Error):
    pass


class LookupError(Error):
    pass


class NamespaceError(Error):
    pass


class Fault(Error):
    def __init__(self, message, code=None, actor=None, detail=None, subcodes=None):
        super(Fault, self).__init__(message)
        self.message = message
        self.code = code
        self.actor = actor
        self.detail = detail
        self.subcodes = subcodes


class ZeepWarning(RuntimeWarning):
    pass
