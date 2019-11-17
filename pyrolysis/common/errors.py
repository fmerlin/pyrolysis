import json
import traceback
from http import HTTPStatus as status
import sys
from pyrolysis.common.converter import application


class PyrolysisException(Exception):
    code = status.INTERNAL_SERVER_ERROR

    def __init__(self, code=None, remote=False,  **data):
        if code:
            self.code = code
        self.remote = remote
        self.data = data

    def put(self, **data):
        self.data.update(data)


class InvalidSwaggerDefinition(PyrolysisException):
    pass


class ClientError(PyrolysisException):
    pass


class ServerError(PyrolysisException):
    pass


class BadRequest(ClientError):
    code = status.BAD_REQUEST


class NotFound(ClientError):
    code = status.NOT_FOUND


class Forbidden(ClientError):
    code = status.FORBIDDEN


class Unauthorized(ClientError):
    code = status.UNAUTHORIZED


class Gone(ClientError):
    code = status.GONE


class InternalServerError(ServerError):
    code = status.INTERNAL_SERVER_ERROR

    def __init__(self, remote=False, exc=None, **data):
        if exc:
            ex_type, ex, tb = sys.exc_info()
            st = traceback.extract_tb(tb)
            lines = [dict(function=e.name, file=e.filename, line=e.line) for e in st]
            self.remote = remote
            self.data = dict(type=type(exc).__name__, message=str(exc), stacktrace=lines)
        else:
            super().__init__(remote=remote, **data)


def check(resp):
    code = resp.status_code
    if code >= 400:
        data = resp.text
        if data is None or len(data) == 0:
            data = {}
        elif resp.headers['content-type'] == application.json:
            data = json.loads(data)
            if not isinstance(data, dict):
                data = {'message': data}
        else:
            data = {'message': data}
        if code == status.BAD_REQUEST:
            raise BadRequest(remote=True, **data)
        if code == status.NOT_FOUND:
            raise NotFound(remote=True, **data)
        if code == status.FORBIDDEN:
            raise Forbidden(remote=True, **data)
        if code == status.UNAUTHORIZED:
            raise Unauthorized(remote=True, **data)
        if code == status.GONE:
            raise Gone(remote=True, **data)
        if code == status.INTERNAL_SERVER_ERROR:
            raise InternalServerError(remote=True, **data)
        if 400 <= code < 500:
            raise ClientError(remote=True, code=code, **data)
        raise ServerError(remote=True, code=code, **data)
