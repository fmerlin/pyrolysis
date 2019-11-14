import json
import datetime
import logging
import platform

import requests
import requests_auth.authentication
from pyrolysis import common, client
from requests.adapters import HTTPAdapter

from pyrolysis.client.checker import create_checker
from pyrolysis.common import mime
from pyrolysis.common.dict_object import DictObject
from pyrolysis.client.method import SwaggerMethod

logger = logging.getLogger(__name__)


class ClientService(mime.Converter):
    def __init__(self, base='http://localhost', server_mode=False, track=False, agent=None,
                 username=None, password=None, api_key=None, proxies=(), port=8000, success_display_time=60,
                 failure_display_time=60, timeout=60, cache=None, max_retries=5, with_checks=True, statsd=None,
                 key=None, cert=None, headers={}, no_oauth2=False):
        self.methods = {}
        self.base = base
        self.cache = None
        self.port = port
        self.timeout = timeout
        self.success_display_time = success_display_time
        self.failure_display_time = failure_display_time
        self.username = username or common.login
        self.password = password
        self.api_key = api_key
        self.proxies = proxies
        self.track = track
        self.definitions = {}
        self.auth = {}
        self.server_mode = server_mode
        self.call_nb = 0
        self.cache = cache
        self.statsd = statsd
        self.key = key
        self.cert = cert
        self.with_checks = with_checks
        self.no_oauth2 = no_oauth2
        self.session = self.create_session(agent, headers, max_retries, track, username)
        self.convert_options = {}

    def create_session(self, agent, headers, max_retries, track, username):
        session = requests.Session()
        session.mount(self.base, HTTPAdapter(max_retries=max_retries))
        session.headers['User-Agent'] = agent or 'Pyrolysis-v' + client.__version__
        session.headers['Accept'] = ' '.join(mime.mimetypes)
        session.headers.update(headers)
        if track:
            session.headers['X-SESSION-LOGIN'] = username
            session.headers['X-SESSION-HOST'] = platform.node()
            session.headers['X-SESSION-START'] = datetime.datetime.today().isoformat()
        return session

    def set_header(self, name, value):
        self.session.headers[name] = value

    def load(self, url=None, file=None, text=None):
        if text:
            swagger = json.loads(text)
        elif file:
            with open(file) as f:
                swagger = json.load(f)
        else:
            resp = self.session.request('GET', url or self.base + '/swagger.json')
            resp.raise_for_status()
            swagger = resp.json()
        for sec, detail1 in swagger.get('securityDefinitions', {}).items():
            if detail1['type'] == 'oauth2':
                if self.no_oauth2:
                    self.auth[sec] = None
                elif self.server_mode:
                    self.auth[sec] = requests_auth.ForwardAuth()
                else:
                    self.auth[sec] = requests_auth.authentication.OAuth2Implicit(
                        detail1['authorizationUrl'],
                        key=sec,
                        additional_authorization_parameters={},
                        redirect_uri_port=self.port,
                        timeout=self.timeout,
                        success_display_time=self.success_display_time,
                        failure_display_time=self.failure_display_time
                    )
            elif detail1['type'] == 'basic':
                self.auth[sec] = requests_auth.authentication.Basic(self.username, self.password)
            elif detail1['type'] == 'apiKey':
                if detail1['in'] == 'query':
                    self.auth[sec] = requests_auth.authentication.QueryApiKey(self.api_key, detail1['name'])
                elif detail1['in'] == 'header':
                    self.auth[sec] = requests_auth.authentication.HeaderApiKey(self.api_key, detail1['name'])

        for df, detail1 in swagger.get('definitions', {}).items():
            self.definitions[df] = create_checker(self, detail1)

        for path, detail1 in swagger.get('paths', {}).items():
            for method, detail2 in detail1.items():
                method_name = detail2['operationId']
                m = SwaggerMethod(self, method_name, method, self.base + path, detail2['summary'], detail2['tags'])
                for security_items in detail2.get('security',[]):
                    lst = [self.auth[security] for security in security_items.keys()]
                    if len(lst) == 1:
                        m.add_auth(lst[0])
                    else:
                        m.add_auth(requests_auth.authentication.Auths(lst))

                self.methods[method_name] = m
                m.load(detail2)

    def add_auth(self, name, auth):
        self.auth[name] = auth

    def add_method(self, name, path, method='GET', summary='', tags=[]):
        m = SwaggerMethod(self, name, method, self.base + path, summary, tags)
        self.methods[name] = m
        return m

    def build(self):
        if len(self.methods) == 0:
            self.load()
        return DictObject(self.methods)

    def __repr__(self):
        return '\n'.join(repr(m) for m in self.methods.values())

    def is_compatible_with(self, prev):
        """
        Check if a service is compatible with another one
        :param prev: the other service
        :return: True if compatible
        """
        for k, v in prev.methods.items():
            if k not in self.methods or not self.methods[k].is_compatible_with(v):
                return False
        return True
