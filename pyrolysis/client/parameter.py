from pyrolysis.client import checker
from pyrolysis.common import errors


class SwaggerParameter:
    def __init__(self, pos, name, required, default_val, doc, checker, encoding, type, enum, parent):
        self.default_val = default_val
        self.required = required
        self.name = name
        self.pos = pos
        self.doc = doc
        self.checker = checker
        self.encoding = encoding
        self.type = type
        self.parent = parent
        self.enum = enum and set(enum)

    def extract(self, *args, **kwargs):
        res = None
        if self.pos < len(args):
            res = args[self.pos]
        elif self.name in kwargs:
            res = kwargs.get(self.name)
        elif self.required:
            raise errors.BadRequest(name=self.name, status='missing')
        if res is None:
            return None
        try:
            srv = self.parent.parent
            return srv.convert(self.encoding, res, checker=self.checker, **srv.convert_options)
        except errors.ClientError as e:
            e.put(name=self.name)
            raise e

    def __repr__(self):
        if self.default_val:
            return '{}: {} ={}'.format(self.name, self.type, self.default_val)
        return '{}: {}'.format(self.name, self.type)

    def is_compatible_with(self, prev):
        return self.name == prev.name and\
               (self.required == prev.required or not self.required) and\
               self.type == prev.type and\
               (self.enum is None or (self.enum & prev.enum) == prev.enum) and\
               self.default_val == prev.default_val


def get_type(parent, details):
    if '$ref' in details:
        name = details['$ref']
        if name[:14] == '#/definitions/' and name[14:] in parent.definitions:
            return name[14:]
        return '#NA'
    s = details.get('schema', details)
    f = s.get('format', None)
    t = s.get('type', None)
    if t == 'string':
        if f == 'date':
            return 'date'
        elif f == 'date-time':
            return 'datetime'
        else:
            return 'str'
    elif t == 'number':
        return 'float'
    elif t == 'bool':
        return 'bool'
    elif t == 'integer' or t == 'long':
        return 'int'
    elif t == 'array':
        items = s.get('items', {})
        return 'List[' + get_type(parent, items) + ']'
    elif t == 'object':
        return 'dict'
    else:
        return '#NA'


def create_parameter(method, details, pos, name, encoding):
    r = details.get('required', False)
    p = details.get('description', '')
    v = details.get('default', None)
    e = details.get('enum', None)
    c = checker.create_checker(method.parent, details) if method.parent.with_checks else None
    t = get_type(method.parent, details)
    return SwaggerParameter(pos, name, r, v, p, c, encoding, t, e, method)


