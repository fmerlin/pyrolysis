import flask

from pyrolysis.server.parameter import Security


class ApiKeyHeader(Security):
    def fetch(self, auth):
        return auth if auth in self.service.api_keys else None

    def get(self):
        return flask.request.headers.get(self.exposed_name or self.name, None)


class ApiKeyParameter(Security):
    def fetch(self, auth):
        return auth if auth in self.service.api_keys else None

    def get(self):
        return flask.request.args.get(self.exposed_name or self.name, None)
