from six.moves import range


class NamePrefixGenerator(object):
    def __init__(self, prefix='_value_'):
        self._num = 1
        self._prefix = prefix

    def get_name(self):
        retval = '%s%d' % (self._prefix, self._num)
        self._num += 1
        return retval


class UniqueNameGenerator(object):
    def __init__(self):
        self._unique_count = {}

    def create_name(self, name):
        if name in self._unique_count:
            self._unique_count[name] += 1
            return '%s__%d' % (name, self._unique_count[name])
        else:
            self._unique_count[name] = 0
            return name


def max_occurs_iter(max_occurs):
    assert max_occurs is not None
    if max_occurs == 'unbounded':
        return range(0, 2**31-1)
    else:
        return range(max_occurs)
