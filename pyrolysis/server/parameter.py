from datetime import date, datetime
from enum import Enum

import flask

from pyrolysis import common as common
from pyrolysis.common import mime, swagger
from pyrolysis.common import errors
from pyrolysis.common.support import check_param, purge


type_class = type


class Parameter:
    def __init__(self, name=None, type=None, required=True, service=None, description='', defaultValue=None, enum=None,
                 array=False, hidden=False, exposed_name=None):
        check_param(name, str, False)
        check_param(type, type_class, False)
        check_param(description, str, False)
        check_param(enum, list, False)
        check_param(required, bool, True)
        self.service = service
        self.enum = enum or isinstance(type, type_class) and issubclass(type, Enum) and list(type) or None
        self.format = None
        self.defaultValue = defaultValue
        self.description = description
        self.required = required and defaultValue is None
        self.type = type
        self.location = type_class(self).__name__.lower()
        self.name = name
        self.array = array
        self.hidden = hidden
        self.exposed_name = exposed_name

    def set_default(self, v):
        if self.defaultValue is None:
            self.defaultValue = v
            self.required = False
        elif self.defaultValue != v:
            raise errors.InvalidSwaggerDefinition(parameter=self.name, default=self.defaultValue, value=v,
                                                  status='conflict')

    def set_service(self, v):
        if self.service is None:
            self.service = v
        elif self.service != v:
            raise errors.InvalidSwaggerDefinition(parameter=self.name, value=v, status='conflict')

    def set_name(self, v):
        if self.name is None:
            self.name = v
        elif self.name != v:
            raise errors.InvalidSwaggerDefinition(parameter=self.name, value=v, status='conflict')

    def set_type(self, v):
        if self.type is None:
            self.type = v
        elif self.type != v:
            raise errors.InvalidSwaggerDefinition(parameter=self.name, type=self.type, value=v, status='conflict')

    def get(self):
        raise NotImplementedError()

    def extract(self):
        res = self.get()
        if res is None:
            if self.required:
                raise errors.BadRequest(parameter=self.name, status='missing')
            else:
                return self.defaultValue
        try:
            mimetype = flask.request.content_type if self.location == 'body' else mime.application.text
            res = self.service.revert(mimetype, res, cls=self.type, many=self.array,
                                            encoding=flask.request.content_encoding)
            if self.enum is not None:
                if res not in self.enum:
                    raise errors.BadRequest(parameter=self.name, enum=self.enum, status='unknown')
            return res
        except errors.BaseException as e:
            e.put(parameter=self.name)
            raise e
        except Exception as e:
            raise errors.BadRequest(parameter=self.name, status='conflict')

    def json(self):
        if issubclass(self.type, Enum):
            tp = 'string'
        else:
            tp = swagger.type_convert.get(self.type, 'object')
        return purge({"name": self.name, "in": self.location, "type": tp,
                      "required": self.required, "description": self.description, "default": self.defaultValue,
                      "format": swagger.format_convert.get(self.type, None), "enum": self.enum})

    def consumes(self):
        return [mime.application.text]

    def __repr__(self):
        t = '[' + ','.join(str(x) for x in self.enum) + ']' if self.enum else self.type.__name__
        if self.defaultValue:
            return self.name + ': ' + t + ' =' + str(self.defaultValue)
        return self.name + ': ' + t


class Header(Parameter):
    def get(self):
        return flask.request.headers.get(self.exposed_name or self.name, None)


class Query(Parameter):
    def get(self):
        return flask.request.args.get(self.exposed_name or self.name, None)


class Cookie(Parameter):
    def get(self):
        return flask.request.cookies.get(self.exposed_name or self.name, None)


class Body(Parameter):
    def get(self):
        return flask.request.data

    def json(self):
        return purge({"name": self.name, "in": "body", "required": self.required, "description": self.description,
                      "schema": {
                          "type": swagger.type_convert.get(self.type, 'object'), "default": self.defaultValue,
                          "format": swagger.format_convert.get(self.type, None), "enum": self.enum
                      }})

    def consumes(self):
        if self.array:
            if self.type in [list, dict, common.pandas_df_type] or self.type in self.service.schemas:
                return [mime.application.json, mime.application.msgpack, mime.application.csv, mime.application.xml, mime.application.pickle]
        else:
            if self.type in [str, int, float, date, datetime]:
                return [mime.application.json, mime.application.msgpack, mime.application.text, mime.application.xml, mime.application.pickle]
        return [mime.application.json, mime.application.msgpack, mime.application.xml, mime.application.pickle]


class Path(Parameter):
    def get(self):
        return flask.request.view_args[self.name]


class Security(Parameter):
    def __init__(self, name=None,  security=None, required=True, service=None, keys=[], exposed_name=None):
        super().__init__(name, type=str, required=required, service=service, description='', defaultValue=None,
                         enum=None, array=False, hidden=True, exposed_name=exposed_name)
        self.keys = keys
        self.security_name = security

    def security(self):
        return {self.security_name: self.keys}

    def fetch(self, auth):
        raise NotImplementedError()

    def extract(self):
        auth = self.get()
        if auth:
            auth = auth.strip()
            return self.fetch(auth)
        if self.required:
            raise errors.Unauthorized(message='No token provided')
        else:
            return None
