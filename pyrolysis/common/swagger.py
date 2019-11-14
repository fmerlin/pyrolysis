from datetime import date, datetime
from pyrolysis.common import pandas_df_type, mime


type_convert = {int: 'integer', float: 'number', str: 'string', date: 'string', datetime: 'string', bool: 'boolean',
             dict: 'object', pandas_df_type: 'object'}
format_convert = {int: 'int32', date: 'date', datetime: 'date-time'}

type_revert = {'integer': int, 'number': float, 'boolean': bool}
str_revert = {'date': date, 'date-time': datetime}


def get_type(data):
    r = data.get('$ref', None)
    if r:
        if r[:14] != '#/definitions/' or r[14:] not in mime.schemas:
            raise Exception()
        return r[14:], False
    t = data.get('type', None)
    if t in type_revert:
        return type_revert[t], False
    elif t == 'string':
        f = data.get('format', None)
        if f in str_revert:
            return str_revert[f], False
    elif t == 'array':
        return get_type(data.get('items', {}))[0], True
    elif t == 'object':
        return get_type(data.get('schema', {}))[0], False
    return str, False
