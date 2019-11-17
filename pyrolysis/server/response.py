from enum import Enum
from http import HTTPStatus as status
from datetime import date, datetime

from pyrolysis import common
from pyrolysis.common import converter, swagger
from pyrolysis.common import errors
from pyrolysis.common.resource import Resource
from pyrolysis.common.support import purge


class Result:
    def __init__(self, parent, type, description, enum=None, array=False):
        self.parent = parent
        self.description = description
        self.enum = enum or issubclass(type, Enum) and list(type)
        self.array = array or type == common.pandas_df_type
        self.type = type

    def produces(self):
        if self.array:
            if self.type in [list, dict, common.pandas_df_type] or self.type in self.parent.schemas:
                return [converter.application.json, converter.application.msgpack, converter.application.csv, converter.application.xml]
        else:
            if self.type in [str, int, float, date, datetime]:
                return [converter.application.json, converter.application.msgpack, converter.application.text, converter.application.xml]
        return [converter.application.json, converter.application.msgpack, converter.application.xml]

    def json(self):
        json = {
            'description': self.description
        }
        if self.type in self.parent.schemas:
            res = {'$ref': '#/definitions/' + str(self.type.__name__)}
        elif self.type == list:
            res = {
                'type': 'array',
                'items': {'type': str}
            }
        elif issubclass(self.type, Enum):
            res = purge({
                'type': str,
                'enum': self.enum
            })
        else:
            res = purge({
                'type': swagger.type_convert.get(self.type),
                'format': swagger.format_convert.get(self.type),
                'enum': self.enum
            })
        if self.array:
            json['schema'] = {'type': 'array', 'items': res}
        else:
            json['schema'] = res
        return json

    def code(self):
        if type == Resource:
            return status.CREATED
        else:
            return status.OK

    def set_type(self, v):
        if self.type is None:
            self.type = v
            if v == common.pandas_df_type:
                self.array = True
            if issubclass(v, Enum):
                self.enum = list(v)
        elif self.type != v:
            raise errors.InvalidSwaggerDefinition(reponse='return', value=v)


class Error:
    def __init__(self, type, description):
        self.type = type
        self.description = description

    def code(self):
        return getattr(self.type(), 'code', status.INTERNAL_SERVER_ERROR)

    def json(self):
        return {
            'description': self.description
        }
