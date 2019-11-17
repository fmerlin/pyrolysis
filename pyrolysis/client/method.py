import logging

import time
import requests.utils

from pyrolysis.client import parameter
from pyrolysis.common import swagger, support, converter
from pyrolysis.common import errors
from pyrolysis.client.parameter import create_parameter
from http import HTTPStatus as status

from pyrolysis.common.support import call_signature
from pyrolysis.common.resource import Resource


logger = logging.getLogger(__name__)


class SwaggerMethod:
    def __init__(self, parent, name, http_method, url, doc, tags):
        self.name = name
        self.parent = parent
        self.parameters = []
        self.body_parameter = None
        self.query_parameters = []
        self.path_parameters = []
        self.header_parameters = []
        self.cookie_parameters = []
        self.return_type = None
        self.http_method = http_method
        self.url = url
        self.tags = tags
        self.auth_methods = []
        self.responses = {}
        self.array = False
        self.pos = 0
        self.__doc__ = doc
        self.encoding = converter.application.json
        self.with_checks = parent.with_checks
        self.statsd = parent.statsd
        self.request_args = {'verify': False, 'timeout': parent.timeout}
        if len(parent.proxies) > 0:
            self.request_args['proxies'] = parent.proxies
        if self.parent.key:
            self.request_args['cert'] = (self.parent.key, self.parent.cert)

    def __call__(self, *args, **kwargs):
        if self.parent.cache and self.http_method == 'GET':
            key = call_signature(self.name, args, kwargs)
            if key in self.parent.cache:
                logger.debug(dict(status="Caching", function=self.name))
                return self.parent.cache[key]
        else:
            key = None

        logger.debug(dict(status="Calling", function=self.name))
        if self.statsd:
            time_start = time.clock()
        request_header = dict((p.name, p.extract(*args, **kwargs)) for p in self.header_parameters)
        request_path = dict((p.name, requests.utils.quote(p.extract(*args, **kwargs))) for p in self.path_parameters)
        request_payload = self.body_parameter.extract(*args, **kwargs) if self.body_parameter else None
        request_parameters = dict((p.name, p.extract(*args, **kwargs)) for p in self.query_parameters)
        request_cookies = dict((p.name, p.extract(*args, **kwargs)) for p in self.cookie_parameters)
        if self.parent.track:
            self.parent.call_nb += 1
            request_header['X-SESSION-REQUEST'] = str(self.parent.call_nb)
        if request_payload:
            request_header['Content-Type'] = self.encoding
        if self.statsd:
            time_prepare = time.clock()
            self.statsd.timing(self.name + '.encoding', time_prepare - time_start)
        response = self.parent.session.request(self.http_method, self.url.format(**request_path),
                                        params=request_parameters,
                                        data=request_payload,
                                        headers=request_header,
                                        cookies=request_cookies,
                                        **self.request_args)
        if self.statsd:
            time_req = time.clock()
            self.statsd.timing(self.name + '.request', time_req - time_prepare)

        errors.check(response)
        logger.debug(dict(status="Valid", function=self.name))
        if response.status_code == status.ACCEPTED:
            loc = response.headers['location']
            return Resource(uri=loc)
        if response.status_code == status.NO_CONTENT or len(response.content) == 0 or 'content-type' not in response.headers:
            return None
        contenttype, encoding = support.decode_contenttype(response.headers['content-type'])
        contentclass = kwargs.get('_return', self.return_type)
        ctrl = response.headers.get('cache-control', 'public')
        res = self.parent.revert(contenttype, response, cls=contentclass, many=self.array, encoding=encoding, **self.parent.convert_options)
        if self.parent.cache and self.http_method == 'GET' and ctrl not in ['no-cache', 'no-store']:
            self.parent.cache[key] = res
        if self.statsd:
            time_end = time.clock()
            self.statsd.timing(self.name + '.decoding', time_end - time_req)
        if contentclass == Resource.__name__:
            return Resource(uri=response.headers['location'],
                            output=res,
                            modified=response.headers['modified'],
                            expires=response.headers['expires'])
        return res

    def load(self, details):
        self.encoding = details.get('consumes', [converter.application.text])[0]
        for name, detail3 in details.get('responses', {}).items():
            self.responses[name] = detail3.get('description', '')
            if name == '200':
                self.return_type, self.array = swagger.get_type(detail3)

        for detail3 in details.get('parameters', []):
            k = detail3['in']
            name = detail3['name']
            encoding = self.encoding if k == 'body' else converter.application.text
            p = create_parameter(self, detail3, self.pos, name, encoding=encoding)
            self.parameters.append(p)
            if k == 'body':
                self.body_parameter = p
            elif k == 'query':
                self.query_parameters.append(p)
            elif k == 'path':
                self.path_parameters.append(p)
            elif k == 'header':
                self.header_parameters.append(p)
            elif k == 'cookie':
                self.cookie_parameters.append(p)
            elif k == 'formData':
                self.body_parameter = p
            else:
                raise errors.InvalidSwaggerDefinition()
            self.pos += 1

    def add_auth(self, param):
        self.auth_methods.append(param)
        if len(self.auth_methods) == 1:
            self.request_args['auth'] = param

    def add_parameter(self, name, type, checker=None, kind='query', required=True, defaultValue=None, description=''):
        encoder = converter.encoders[self.encoding if kind == 'body' else converter.application.text]
        p = parameter.SwaggerParameter(self.pos, name, required, defaultValue, description, checker, encoder, type, self)
        self.parameters.append(p)
        self.pos += 1
        if kind == 'query':
            self.query_parameters.append(p)
        elif kind == 'path':
            self.path_parameters.append(p)
        elif kind == 'header':
            self.header_parameters.append(p)
        elif kind == 'cookie':
            self.cookie_parameters.append(p)
        elif kind == 'body':
            self.body_parameter = p
        else:
            raise errors.InvalidSwaggerDefinition()
        return p

    def __repr__(self):
        n = len(self.header_parameters) + len(self.path_parameters) + len(self.query_parameters)
        if self.body_parameter:
            n += 1
        par = [None] * n
        for p in self.header_parameters:
            par[p.pos] = p
        for p in self.path_parameters:
            par[p.pos] = p
        for p in self.query_parameters:
            par[p.pos] = p
        if self.body_parameter:
            par[self.body_parameter.pos] = self.body_parameter
        return self.name + '(' + ', '.join(repr(x) for x in par) + ') -> ' + self.return_type

    def is_compatible_with(self, prev):
        if len(prev.parameters) > len(self.parameters):
            return False
        for i in range(len(prev.parameters)):
            if not self.parameters[i].is_compatible_with(prev.parameters[i]):
                return False
        for i in range(len(prev.parameters), len(self.parameters)):
            if self.parameters[i].required:
                return False
        return prev.name == self.name and prev.return_type == self.return_type
