import requests


class Transport(object):

    def __init__(self, cache=None):
        self.cache = cache

    def load(self, url):
        if self.cache:
            response = self.cache.get(url)
            if response:
                return bytes(response)

        response = requests.get(url)

        if self.cache:
            self.cache.add(url, response.content)

        return response.content

    def post(self, address, message, headers):
        response = requests.post(address, data=message, headers=headers)
        return response
