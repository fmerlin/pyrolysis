import flask

from pyrolysis.server.parameter import Security


class ApiKeyHeader(Security):
    def fetch(self, auth):
        return auth if auth in self.service.api_keys else None

    def get(self):
        return flask.request.headers.get('x-api-key', flask.request.args.get('api_key', None))
