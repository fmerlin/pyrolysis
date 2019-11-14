from pyrolysis.common import errors


class DictObject:
    def __init__(self, map):
        self.map = map

    def __getattr__(self, item):
        if item in self.map:
            return self.map[item]
        raise errors.NotFound(method=item)

    def __repr__(self):
        return '\n'.join(repr(x) for x in self.map)
