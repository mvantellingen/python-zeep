import requests

from zeep.cache import SqliteCache


class Transport(object):

    def __init__(self, cache=None, timeout=300, verify=True, http_auth=None):
        self.cache = cache or SqliteCache()
        self.timeout = timeout
        self.verify = verify
        self.http_auth = http_auth

    def load(self, url):
        if self.cache:
            response = self.cache.get(url)
            if response:
                return bytes(response)

        response = requests.get(url, timeout=self.timeout, verify=self.verify, auth=self.http_auth)

        if self.cache:
            self.cache.add(url, response.content)

        return response.content

    def post(self, address, message, headers):
        response = requests.post(
            address, data=message, headers=headers, verify=self.verify, auth=self.http_auth
        )
        return response

    def get(self, address, params, headers):
        response = requests.get(
            address, params=params, headers=headers, verify=self.verify, auth=self.http_auth
        )
        return response
