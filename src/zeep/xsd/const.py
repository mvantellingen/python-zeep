from lxml import etree

NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
NS_XSD = 'http://www.w3.org/2001/XMLSchema'


def xsi_ns(localname):
    return etree.QName(NS_XSI, localname)


def xsd_ns(localname):
    return etree.QName(NS_XSD, localname)


class _StaticIdentity(object):
    def __init__(self, val):
        self.__value__ = val

    def __repr__(self):
        return self.__value__


NotSet = _StaticIdentity('NotSet')
SkipValue = _StaticIdentity('SkipValue')
