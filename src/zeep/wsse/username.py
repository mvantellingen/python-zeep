import base64
import hashlib
import os

from zeep import ns
from zeep.wsse import utils


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
    username_token_profile_ns = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0'  # noqa
    soap_message_security_ns = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0'    # noqa

    def __init__(self, username, password=None, password_digest=None,
                 use_digest=False, nonce=None, created=None, plaintext_nonce=False):
        self.username = username
        self.password = password
        self.password_digest = password_digest
        self.nonce = nonce
        self.created = created
        self.use_digest = use_digest
        self.plaintext_nonce = plaintext_nonce

    def apply(self, envelope, headers):
        security = utils.get_security_header(envelope)

        # The token placeholder might already exists since it is specified in
        # the WSDL.
        token = security.find('{%s}UsernameToken' % ns.WSSE)
        if token is None:
            token = utils.WSSE.UsernameToken()
            security.append(token)

        # Create the sub elements of the UsernameToken element
        elements = [
            utils.WSSE.Username(self.username)
        ]
        if self.password is not None or self.password_digest is not None:
            if self.use_digest:
                elements.extend(self._create_password_digest())
            else:
                elements.extend(self._create_password_text())

        token.extend(elements)
        return envelope, headers

    def verify(self, envelope):
        pass

    def _create_password_text(self):
        r = [
            utils.WSSE.Password(
                self.password,
                Type='%s#PasswordText' % self.username_token_profile_ns)
        ]
        if self.plaintext_nonce:
            nonce = self._create_nonce()
            r.append(utils.WSSE.Nonce(
                nonce.decode('utf-8'),
                EncodingType='%s#Base64Binary' % self.soap_message_security_ns
            ))
            timestamp = utils.get_timestamp(self.created)
            r.append(utils.WSU.Created(timestamp))
        return r

    def _create_nonce(self):
        if self.nonce:
            nonce = self.nonce.encode('utf-8')
        else:
            nonce = os.urandom(16)
        return base64.b64encode(nonce)

    def _create_password_digest(self):
        nonce = self._create_nonce()
        timestamp = utils.get_timestamp(self.created)

        # digest = Base64 ( SHA-1 ( nonce + created + password ) )
        if not self.password_digest:
            digest = base64.b64encode(
                hashlib.sha1(
                    nonce + timestamp.encode('utf-8') +
                    self.password.encode('utf-8')
                ).digest()
            ).decode('ascii')
        else:
            digest = self.password_digest

        return [
            utils.WSSE.Password(
                digest,
                Type='%s#PasswordDigest' % self.username_token_profile_ns
            ),
            utils.WSSE.Nonce(
                nonce.decode('utf-8'),
                EncodingType='%s#Base64Binary' % self.soap_message_security_ns
            ),
            utils.WSU.Created(timestamp)
        ]
