"""Basic implementation to support SOAP-Attachments

See https://www.w3.org/TR/SOAP-attachments

"""

import base64
import pathlib
import io
import mimetypes

from typing import Union

from cached_property import cached_property
from requests.structures import CaseInsensitiveDict

from requests_toolbelt.multipart.encoder import MultipartEncoder, Part


class MessageMultipartEncoder(MultipartEncoder):
    def _prepare_parts(self):
        self.parts = []

        for field in self._iter_fields():
            if "Content-Disposition" in field.headers:
                del field.headers["Content-Disposition"]

            self.parts.append(Part.from_field(field, self.encoding))

        self._iter_parts = iter(self.parts)


class MessagePack:
    def __init__(self, parts):
        self._parts = parts

    def __repr__(self):
        return "<MessagePack(attachments=[%s])>" % (
            ", ".join(repr(a) for a in self.attachments)
        )

    @property
    def root(self):
        return self._root

    def _set_root(self, root):
        self._root = root

    @cached_property
    def attachments(self):
        """Return a list of attachments.

        :rtype: list of Attachment

        """
        return [Attachment(part) for part in self._parts]

    def get_by_content_id(self, content_id):
        """get_by_content_id

        :param content_id: The content-id to return
        :type content_id: str
        :rtype: Attachment

        """
        for attachment in self.attachments:
            if attachment.content_id == content_id:
                return attachment


class Attachment:
    def __init__(self, part):
        encoding = part.encoding or "utf-8"
        self.headers = CaseInsensitiveDict(
            {k.decode(encoding): v.decode(encoding) for k, v in part.headers.items()}
        )
        self.content_type = self.headers.get("Content-Type", None)
        self.content_id = self.headers.get("Content-ID", None)
        self.content_location = self.headers.get("Content-Location", None)
        self._part = part

    def __repr__(self):
        return "<Attachment(%r, %r)>" % (self.content_id, self.content_type)

    @cached_property
    def content(self):
        """Return the content of the attachment

        :rtype: bytes or str

        """
        encoding = self.headers.get("Content-Transfer-Encoding", None)
        content = self._part.content

        if encoding == "base64":
            return base64.b64decode(content)
        elif encoding == "binary":
            return content.strip(b"\r\n")
        else:
            return content


class AttachmentEncodable:
    def __init__(
        self,
        name: str = None,
        data: Union[io.IOBase, bytes] = b"",
        content_type: str = None,
        transfer_encoding: str = "binary",
    ):
        """
        data can be a stream or a bytes object.
        """

        self.data = data

        # What follows are best-guess heuristics for determining name and content type.
        if isinstance(data, (io.TextIOWrapper, io.BufferedReader)):
            if isinstance(data, io.TextIOWrapper):
                self.transfer_encoding = "8bit"
            elif isinstance(data, io.BufferedReader):
                self.transfer_encoding = "binary"

            file_path = pathlib.Path(data.name)

            if name is None:
                name = file_path.name

            if content_type is None:
                content_type, encoding = mimetypes.guess_type(name)

                if content_type is None:
                    if isinstance(data, io.TextIOWrapper):
                        content_type = "text/plain"
                    else:
                        content_type = "application/octet-stream"
        else:
            if name is None:
                name = "attachment"

        self.name = name
        self.data = data
        self.content_type = content_type

    def to_multipart_field_def(self):
        return (
            None,
            self.data,
            self.content_type,
            {
                "Content-ID": f"<{self.name}>",
                "Content-Transfer-Encoding": self.transfer_encoding,
            },
        )

    def __repr__(self):
        return f"AttachmentEncodable(name={self.name}, data={repr(self.data)}, content_type={self.content_type}"

    def __str__(self):
        return repr(self)


class AttachmentCollection(list):
    def __init__(self, *args, **kwargs):
        args = list(args)

        for i, arg in enumerate(args):
            if isinstance(arg, (io.TextIOWrapper, io.BufferedReader)):
                args[i] = AttachmentEncodable(data=arg)
            if isinstance(arg, tuple):
                if len(arg) == 2:
                    args[i] = AttachmentEncodable(name=arg[0], data=arg[1])
                elif len(arg) == 3:
                    args[i] = AttachmentEncodable(
                        name=arg[0], data=arg[1], content_type=arg[2]
                    )

        super().__init__(args, **kwargs)

    def to_multipart_field_defs(self, fields_dict=None):
        if fields_dict is None:
            fields_dict = {}

        for attachment in self:
            fields_dict[attachment.name] = attachment.to_multipart_field_def()

        return fields_dict
