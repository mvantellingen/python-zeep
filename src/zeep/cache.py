import base64
import datetime
import os
import sqlite3


class SqliteCache(object):
    _version = '1'

    def __init__(self, persistent=True, path=None, timeout=3600):
        self._timeout = timeout

        # Create db
        if persistent:
            if not path:
                path = os.path.expanduser('~/.pyzeep.cache.db')
        else:
            path = ':memory:'

        self._db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)

        cursor = self._db.cursor()
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS request
                (created timestamp, url text, content text)
            """)

    def add(self, url, content):
        data = self._encode_data(content)
        cursor = self._db.cursor()
        cursor.execute("DELETE FROM request WHERE url = ?", (url,))
        cursor.execute(
            "INSERT INTO request (created, url, content) VALUES (?, ?, ?)",
            (datetime.datetime.utcnow(), url, data))
        self._db.commit()

    def get(self, url):
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT created, content FROM request WHERE url=?", (url, ))
        rows = cursor.fetchall()
        if rows:
            created, data = rows[0]
            offset = (
                datetime.datetime.utcnow() -
                datetime.timedelta(seconds=self._timeout))
            if not self._timeout or created > offset:
                return self._decode_data(data)

    def _encode_data(self, data):
        data = base64.b64encode(data)
        return self._version_string + data

    def _decode_data(self, data):
        if data.startswith(self._version_string):
            return base64.b64decode(data[len(self._version_string):])

    @property
    def _version_string(self):
        prefix = u'$ZEEP:%s$' % self._version
        return bytes(prefix.encode('ascii'))
