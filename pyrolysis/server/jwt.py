import flask
import requests
import json
import jwt
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from requests.adapters import HTTPAdapter
from pyrolysis.server.parameter import Security
from pyrolysis.common import support
from pyrolysis.common import errors
from pyrolysis.common.cache import caching


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
                certificate_text = b"-----BEGIN CERTIFICATE-----\n" + x5c.encode('utf-8') + b"\n-----END CERTIFICATE-----"
                certificate = load_pem_x509_certificate(certificate_text, default_backend())
                return certificate.public_key()
        raise errors.Unauthorized(message='no tid in id-token')


    def fetch(self, bearer):
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
        self.service.set_user(user)
        return user

    def get(self):
        req = flask.request
        auth = req.headers.get('authorization', None)
        if auth and auth[:7] == 'Bearer ':
            return auth[7:]
        return req.headers.get('bearer', req.args.get('id_token', None))
