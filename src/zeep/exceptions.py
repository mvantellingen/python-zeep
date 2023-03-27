class Error(Exception):
    def __init__(self, message: str = ""):
        super(Exception, self).__init__(message)
        self.message = message

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.message)


class XMLSyntaxError(Error):
    def __init__(self, *args, **kwargs):
        self.content = kwargs.pop("content", None)
        super().__init__(*args, **kwargs)


class XMLParseError(Error):
    def __init__(self, *args, **kwargs):
        self.filename = kwargs.pop("filename", None)
        self.sourceline = kwargs.pop("sourceline", None)
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        location = None
        if self.filename and self.sourceline:
            location = "%s:%s" % (self.filename, self.sourceline)
        if location:
            return "%s (%s)" % (self.message, location)
        return self.message


class UnexpectedElementError(Error):
    pass


class WsdlSyntaxError(Error):
    pass


class TransportError(Error):
    def __init__(self, message: str = "", status_code=0, content=None):
        super().__init__(message)
        self.status_code = status_code
        self.content = content


class LookupError(Error):
    def __init__(self, *args, **kwargs):
        self.qname = kwargs.pop("qname", None)
        self.item_name = kwargs.pop("item_name", None)
        self.location = kwargs.pop("location", None)
        super().__init__(*args, **kwargs)


class NamespaceError(Error):
    pass


class Fault(Error):
    def __init__(self, message: str, code=None, actor=None, detail=None, subcodes=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.actor = actor
        self.detail = detail
        self.subcodes = subcodes


class ZeepWarning(RuntimeWarning):
    pass


class ValidationError(Error):
    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path", [])
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        if self.path:
            path = ".".join(str(x) for x in self.path)
            return "%s (%s)" % (self.message, path)
        return self.message


class SignatureVerificationFailed(Error):
    pass


class IncompleteMessage(Error):
    pass


class IncompleteOperation(Error):
    pass


class DTDForbidden(Error):
    def __init__(self, name, sysid, pubid):
        super(DTDForbidden, self).__init__()
        self.name = name
        self.sysid = sysid
        self.pubid = pubid

    def __str__(self):
        tpl = "DTDForbidden(name='{}', system_id={!r}, public_id={!r})"
        return tpl.format(self.name, self.sysid, self.pubid)


class EntitiesForbidden(Error):
    def __init__(self, name, content):
        super(EntitiesForbidden, self).__init__()
        self.name = name
        self.content = content

    def __str__(self):
        tpl = "EntitiesForbidden(name='{}', content={!r})"
        return tpl.format(self.name, self.content)
