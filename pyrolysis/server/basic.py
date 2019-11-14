import flask
from pyrolysis.server.parameter import Security


class BasicHeader(Security):
    def fetch(self, auth):
        if auth.startswith('Basic'):
            authorization = flask.request.authorization
            if self.service.passwords.get(authorization.username, None) == authorization.password:
                self.service.set_user(authorization.username)
                return authorization.username

    def get(self):
        return flask.request.headers.get('authorization', None)
