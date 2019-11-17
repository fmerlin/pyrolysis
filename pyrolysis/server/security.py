import itertools
import json
from abc import ABC

import flask
import jwt
import requests
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from flask import g
from requests.adapters import HTTPAdapter

from pyrolysis.common import errors, support
from pyrolysis.common.cache import caching


class Security(ABC):
    def __init__(self, name):
        self.name = name
        self.roles = []

    def add_role(self, role):
        res = Role(role, self)
        self.roles.append(res)
        return res

    def get_roles(self):
        return []


class MultiRole:
    def __init__(self, x) -> None:
        if isinstance(x, Role):
            self.roles = frozenset([frozenset([x])])
        elif isinstance(x, MultiRole):
            self.roles = x.roles
        else:
            self.roles = x

    def __and__(self, other):
        if isinstance(other, MultiRole):
            return MultiRole(frozenset([a.union(b) for a, b in itertools.product(self.roles, other.roles)]))
        if isinstance(other, Role):
            return MultiRole(frozenset([r.union(frozenset([other])) for r in self.roles]))
        return self

    def __or__(self, other):
        if isinstance(other, MultiRole):
            return MultiRole(self.roles.union(other.roles))
        if isinstance(other, Role):
            return MultiRole(self.roles.union(frozenset([other])))
        return self

    def get_parents(self):
        return set([r2.parent for r1 in self.roles for r2 in r1])

    def get_role_names(self):
        res = []
        for r1 in self.roles:
            securities = set([r2.parent for r2 in r1])
            res.append(dict((s.name, [r2.name for r2 in r1 if r2.parent == s]) for s in securities))
        return res

    def check_roles(self):
        parents = set([r2.parent for r1 in self.roles for r2 in r1])
        res = dict((p.name, p.get_roles()) for p in parents)
        for r1 in self.roles:
            for r2 in r1:
                if r2.name not in res[r2.parent.name]:
                    break
            else:
                return
        for p in parents:
            if isinstance(p, JWTHeader):
                raise errors.Unauthorized(authorizationUrl=p.authorizationUrl)
        raise errors.Unauthorized()

    def get_service_definition(self):
        return dict((s.name, s.definition()) for s in self.get_parents())

    def __str__(self):
        return ' or '.join(' and '.join(str(r1)) for r2 in self.roles for r1 in r2)


class Role:
    def __init__(self, name: str, parent: Security):
        self.name = name
        self.parent = parent

    def __and__(self, other):
        if isinstance(other, MultiRole):
            return other and self
        return MultiRole(frozenset([frozenset([self, other])]))

    def __or__(self, other):
        if isinstance(other, MultiRole):
            return other or self
        return MultiRole(frozenset([frozenset([self]), frozenset([other])]))

    def __hash__(self):
        return hash(self.name) + hash(self.parent.name)

    def __eq__(self, other):
        if isinstance(other, Role):
            return self.name == other.name and self.parent == other.paent
        return False

    def __str__(self):
        return self.name


class BasicHeader(Security):
    def get_roles(self):
        authorization = flask.request.authorization
        g.username = authorization.username
        return self.fetch_roles(authorization.username, authorization.password)

    def fetch_roles(self, username, password):
        return []

    def definition(self):
        return dict(type='basic')


class ApiKeyHeader(Security):
    def __init__(self, name, header):
        super().__init__(name)
        self.header = header

    def get_roles(self):
        g.apikey = key = flask.request.headers.get(self.header, None)
        return self.fetch_roles(key)

    def fetch_roles(self, key):
        return []

    def definition(self):
        return {'type': 'apiKey', 'in': 'header', 'name': self.header}


class ApiKeyParameter(Security):
    def __init__(self, name, parameter):
        super().__init__(name)
        self.parameter = parameter

    def get_roles(self):
        g.apikey = key = flask.request.args.get(self.parameter or self.name, None)
        return self.fetch_roles(key)

    def fetch_roles(self, key):
        return []

    def definition(self):
        return {'type': 'apiKey', 'in': 'query', 'name': self.parameter}


class JWTHeader(Security):
    max_retries = 5
    options = {
        'verify_signature': True,
        'verify_exp': True,
        'verify_nbf': True,
        'verify_iat': True,
        'verify_aud': False,
        'require_exp': True,
        'require_iat': True,
        'require_nbf': True
    }

    def __init__(self, name, authorizationUrl, flow='implicit', tokenUrl=None, refreshUrl=None, required=True):
        super().__init__(name)
        support.check_param(flow, ['implicit', 'password', 'clientCredentials', 'authorizationCode'], True)
        self.authorizationUrl = authorizationUrl
        self.flow = flow
        self.tokenUrl = tokenUrl
        self.refreshUrl = refreshUrl
        self.required = required

    @caching()
    def get_public_key(self, idp, kid):
        try:
            s = requests.Session()
            s.mount(idp, HTTPAdapter(max_retries=self.max_retries))
            r = s.get(idp + 'common/discovery/keys')
            keys_json = r.json()
        except ConnectionError:
            raise errors.Unauthorized(message='Cannot connect to ' + idp + 'common/discovery/keys')

        for key in keys_json.get('keys', []):
            if key.get('kid', '') == kid:
                x5c = key.get('x5c', [''])[0]
                certificate_text = b"-----BEGIN CERTIFICATE-----\n" + x5c.encode(
                    'utf-8') + b"\n-----END CERTIFICATE-----"
                certificate = load_pem_x509_certificate(certificate_text, default_backend())
                return certificate.public_key()
        raise errors.Unauthorized(message='no tid in id-token')

    def get_roles(self):
        req = flask.request
        bearer = req.headers.get('bearer', req.args.get('id_token', None))
        (jwt_header, jwt_body, jwt_sign) = bearer.split('.')

        json_str_header = support.decode_base64(jwt_header)
        json_header = json.loads(json_str_header.decode('unicode_escape'))
        body_str_json = support.decode_base64(jwt_body)
        body_json = json.loads(body_str_json.decode('unicode_escape'))

        # validate
        kid = json_header.get('kid', None)
        iss = body_json.get('iss', None)
        tid = body_json.get('tid', None)
        if iss is None:
            raise errors.Unauthorized(message='no iss (i.e. identity provider) in id-token')
        if tid is None:
            raise errors.Unauthorized(message='no tid in id-token')
        idp = iss.split(tid)[0]
        public_key = self.get_public_key(idp, kid)
        try:
            jwt.decode(bearer, public_key, options=self.options)
        except jwt.InvalidTokenError:
            raise errors.Unauthorized(message='invalid token')

        # extract
        upn = body_json.get('upn')
        if upn is None:
            raise errors.Unauthorized(message='no upn (i.e. engie userid) in id-token')
        user = upn.split('@')[0]
        g.username = user
        return self.fetch_roles(body_json)

    def fetch_roles(self, user):
        return []

    def definition(self):
        return {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}
