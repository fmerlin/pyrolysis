import datetime
from enum import Enum

from pyrolysis.common import errors


def type_checker(*types):
    def check(val):
        for t in types:
            if isinstance(val, t):
                return
        raise errors.BadRequest(type=type(val), status='unknown')
    return check


def array_checker(checker):
    def check(val):
        for x in val:
            checker.check(x)
    return check


def enum_checker(enum):
    def check(val):
        if val in enum:
            pass
        elif isinstance(val, Enum) and val.name in enum:
            pass
        else:
            raise errors.BadRequest(val=val)
    return check


def dict_checker(fields, mandatory):
    def check(val):
        if not isinstance(val,dict):
            raise errors.BadRequest(type=type(val), status='unknown')
        if not mandatory.issubset(set(val.keys())):
            raise errors.BadRequest(fields=mandatory.sub(set(val.keys())), status='missing')
        if len(fields) > 0:
            for k,v in val.items():
                if k not in fields:
                    raise errors.BadRequest(field=k, status='unknown')
                fields[k].check(v)
    return check


def forward_checker(parent, name):
    def check(val):
        return parent.definitions[name](val)
    return check


def create_checker(parent, details):
    s = details.get('schema', details)
    if '$ref' in s:
        name = s['$ref']
        if name[:14] == '#/definitions/':
            name = name[14:]
            if name in parent.definitions:
                return parent.definitions[name]
            return forward_checker(parent, name)
        raise errors.InvalidSwaggerDefinition(ref=name, status='unknown')
    f = s.get('format', None)
    t = s.get('type', None)
    if t == 'string':
        if 'enum' in details:
            c = enum_checker(s['enum'])
        elif f == 'date':
            c = type_checker(datetime.date)
        elif f == 'date-time':
            c = type_checker(datetime.date, datetime.datetime)
        else:
            c = type_checker(str)
    elif t == 'number':
        c = type_checker(float, int)
    elif t == 'boolean':
        c = type_checker(bool)
    elif t == 'integer' or t == 'long':
        c = type_checker(int)
    elif t == 'array':
        items = s.get('items', {})
        c = array_checker(create_checker(parent, items))
    elif t == 'file':
        c = type_checker(str)
    elif t == 'object':
        mandatory = s != details and s.get('required', []) or []
        fields = s.get('properties', {})
        c = dict_checker(dict((k, create_checker(parent, v)) for k, v in fields.items()), set(mandatory))
    elif t in parent.definitions:
        c = parent.definitions[t]
    else:
        raise errors.InvalidSwaggerDefinition(type=t, status='unknown')
    return c
