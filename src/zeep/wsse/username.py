import base64
import hashlib
import os

from lxml.builder import ElementMaker

from zeep.wsse import utils

NSMAP = {
    'wsse': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd',
    'wsu': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd',
}
WSSE = ElementMaker(namespace=NSMAP['wsse'])
WSU = ElementMaker(namespace=NSMAP['wsu'])


class UsernameToken(object):
    """UsernameToken Profile 1.1

    https://docs.oasis-open.org/wss/v1.1/wss-v1.1-spec-os-UsernameTokenProfile.pdf

    Example response using PasswordText::

        <wsse:Security>
          <wsse:UsernameToken>
            <wsse:Username>scott</wsse:Username>
            <wsse:Password Type="wsse:PasswordText">password</wsse:Password>
          </wsse:UsernameToken>
        </wsse:Security>

    Example using PasswordDigest::

        <wsse:Security>
          <wsse:UsernameToken>
            <wsse:Username>NNK</wsse:Username>
            <wsse:Password Type="wsse:PasswordDigest">
                weYI3nXd8LjMNVksCKFV8t3rgHh3Rw==
            </wsse:Password>
            <wsse:Nonce>WScqanjCEAC4mQoBE07sAQ==</wsse:Nonce>
            <wsu:Created>2003-07-16T01:24:32Z</wsu:Created>
          </wsse:UsernameToken>
        </wsse:Security>

    """
    namespace = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0'  # noqa

    def __init__(self, username, password, use_digest=False):
        self.username = username
        self.password = password
        self.use_digest = use_digest

    def sign(self, envelope, headers):
        security = utils.get_security_header(envelope)

        # The token placeholder might already exists since it is specified in
        # the WSDL.
        token = security.find('{%s}UsernameToken' % NSMAP['wsse'])
        if token is None:
            token = WSSE.UsernameToken()
            security.append(token)

        # Create the sub elements of the UsernameToken element
        elements = [
            WSSE.Username(self.username)
        ]
        if self.password is not None:
            if self.use_digest:
                elements.extend(self._create_password_digest())
            else:
                elements.extend(self._create_password_text())

        token.extend(elements)
        return envelope, headers

    def verify(self, envelope):
        pass

    def _create_password_text(self):
        return [
            WSSE.Password(
                self.password, Type='%s#PasswordText' % self.namespace)
        ]

    def _create_password_digest(self):
        nonce = os.urandom(16)
        timestamp = utils.get_timestamp()

        # digest = Base64 ( SHA-1 ( nonce + created + password ) )
        digest = base64.b64encode(
            hashlib.sha1(
                nonce + timestamp.encode('utf-8') + self.password.encode('utf-8')
            ).digest())

        return [
            WSSE.Password(
                digest.decode('ascii'),
                Type='%s#PasswordDigest' % self.namespace
            ),
            WSSE.Nonce(base64.b64encode(nonce).decode('ascii')),
            WSU.Created(timestamp)
        ]
