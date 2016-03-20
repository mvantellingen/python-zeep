import datetime
import os
import sqlite3


class SqliteCache(object):
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
        cursor = self._db.cursor()
        cursor.execute("DELETE FROM request WHERE url = ?", (url,))
        cursor.execute(
            "INSERT INTO request (created, url, content) VALUES (?, ?, ?)",
            (datetime.datetime.utcnow(), url, content))
        self._db.commit()

    def get(self, url):
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT created, content FROM request WHERE url=?", (url, ))
        rows = cursor.fetchall()
        if rows:
            created, content = rows[0]
            offset = (
                datetime.datetime.utcnow() -
                datetime.timedelta(seconds=self._timeout))
            if not self._timeout or created > offset:
                return content
