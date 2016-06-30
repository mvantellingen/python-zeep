from six.moves import range


class UniqueAttributeName(object):
    def __init__(self):
        self._num = 1

    def get_name(self):
        retval = '_value_%d' % self._num
        self._num += 1
        return retval


def max_occurs_iter(max_occurs):
    assert max_occurs is not None
    if max_occurs == 'unbounded':
        return range(0, 2**31-1)
    else:
        return range(max_occurs)
