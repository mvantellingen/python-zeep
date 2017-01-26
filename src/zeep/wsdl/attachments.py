"""Basic implementation to support SOAP-Attachments

See https://www.w3.org/TR/SOAP-attachments

"""
import base64
from io import BytesIO

from cached_property import cached_property
from requests.structures import CaseInsensitiveDict


class MessagePack(object):
    def __init__(self, parts):
        self._parts = parts

    @property
    def root(self):
        return self._root

    def _set_root(self, root):
        self._root = root

    @cached_property
    def attachments(self):
        return [Attachment(part) for part in self._parts]

    def get_by_content_id(self, content_id):
        for attachment in self.attachments:
            if attachment.content_id == content_id:
                return attachment


class Attachment(object):
    def __init__(self, part):

        self.headers = CaseInsensitiveDict({
            k.decode(part.encoding): v.decode(part.encoding)
            for k, v in part.headers.items()
        })
        self.content_type = self.headers.get('Content-Type', None)
        self.content_id = self.headers.get('Content-ID', None)
        self.content_location = self.headers.get('Content-Location', None)
        self._part = part

    @cached_property
    def data(self):
        encoding = self.headers.get('Content-Transfer-Encoding', None)
        content = self._part.content

        if encoding == 'base64':
            content = base64.b64decode(content)
            return BytesIO(content)
        elif encoding == 'binary':
            return BytesIO(content)
        else:
            return content
