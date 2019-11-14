import datetime
import json
import time
import urllib.parse
import uuid
from collections import Mapping
from functools import wraps
from http import HTTPStatus as status

import flask
import flask_swagger
import yaml
from marshmallow_jsonschema import JSONSchema

from pyrolysis import common as common
from pyrolysis.common import mime, support
from pyrolysis.common import errors, doc
from pyrolysis.common.mime import application, JSONEncoder2
from pyrolysis.common.resource import Resource
from pyrolysis.server.api_key import ApiKeyHeader
from pyrolysis.server.basic import BasicHeader
from pyrolysis.server.jwt import JWTHeader
from pyrolysis.server.parameter import Body, Path, Query, Security
from pyrolysis.server.response import Result


def has_browser():
    return flask.request.user_agent.browser in ['chrome', 'msie', 'firefox', 'opera']


class Service(mime.Converter):
    securities = {}
    passwords = {}
    api_keys = set()
    cached_spec = None
    log_filter = None

    def __init__(self, flask, base='', version='', description='', health=True, statsd=None,
                 socket_app=None):
        self.flask = flask
        self.base = base
        self.logger = flask.logger
        self.name = flask.name
        self.statsd = statsd
        self.info = {'title': self.name, 'version': version, 'description': description}

        if health:
            @flask.route('/health')
            def health():
                    return "OK " + datetime.datetime.now().isoformat(), 200

        self.socket_app = socket_app

        @flask.route(base + "/")
        @flask.route(base + "/swagger.json")
        def spec():
            if self.cached_spec is None:
                json_schema = JSONSchema()
                definitions = dict((k, list(json_schema.dump(v)['definitions'].values())[0]) for k, v in self.schemas.items())
                spec = flask_swagger.swagger(flask, template=dict(definitions=definitions,
                                                                  info=self.info,
                                                                  securityDefinitions=self.securities))
                self.cached_spec = json.dumps(spec, cls=JSONEncoder2, allow_nan=False)
            return self.cached_spec

        @flask.errorhandler(errors.BaseException)
        def handle_error_base(e):
            return json.dumps(e.data, cls=JSONEncoder2, allow_nan=False), e.code

        @flask.errorhandler(Exception)
        def handle_error(e):
            flask.logger.exception('Uncaught exception')
            return json.dumps({'type': type(e), 'message': str(e)}, cls=JSONEncoder2, allow_nan=False), status.INTERNAL_SERVER_ERROR

    def get(self, path, **options):
        return self.operation(path, methods=['GET', 'HEAD'], **options)

    def post(self, path, **options):
        return self.operation(path, methods=['POST'], **options)

    def put(self, path, **options):
        return self.operation(path, methods=['PUT'], **options)

    def delete(self, path, **options):
        return self.operation(path, methods=['DELETE'], **options)

    def operation(self, path, tags=None, parameters=None, responses=None, operationId=None, summary=None,
                  dump=False, cache=None, **options):
        support.check_param(tags, list, False)
        support.check_param(responses, dict, False)
        support.check_param(operationId, str, False)
        support.check_param(summary, str, False)
        support.check_param(dump, bool, False)
        if not parameters:
            parameters = []

        def decorator(fn):
            op = operationId or fn.__name__
            n = fn.__code__.co_argcount
            v = fn.__code__.co_varnames
            c = fn.__defaults__
            summary, desc, desc_params, desc_return, desc_raise = doc.parse_docstring(fn.__doc__)
            types = getattr(fn, '__annotations__', {})
            security = []
            for i in range(n):
                name = v[i]
                cst = c[i] if c and i < len(c) else None
                tp = types.get(name, str)
                if i < len(parameters):
                    parameters[i].set_service(self)
                    parameters[i].set_name(name)
                    if name in types:
                        parameters[i].set_type(tp)
                    if name in desc_params:
                        parameters[i].description = desc_params[name]
                    if c and i < len(c):
                        parameters[i].set_default(c[i])
                    if isinstance(parameters[i], Security):
                        security.append(parameters[i].security())
                elif '<'+name+'>' in path:
                    parameters.append(Path(name, tp, service=self, defaultValue=cst, description=desc_params.get(name, '')))
                elif issubclass(tp, Mapping) or tp.__name__ in self.schemas or tp == common.pandas_df_type:
                    parameters.append(Body(name, tp, service=self, defaultValue=cst, description=desc_params.get(name, '')))
                else:
                    parameters.append(Query(name, tp, service=self, defaultValue=cst, description=desc_params.get(name, '')))
            return_type = types.get('return', None)
            toadd = True
            produces = []
            resp = responses or []
            for v in resp:
                if isinstance(v, Result):
                    if return_type:
                        v.set_type(return_type)
                    if desc_return:
                        v.description = desc_return
                    toadd = False
                    produces = v.produces()

            if toadd and return_type:
                r = Result(parent=self, type=return_type, description=desc_return)
                resp.append(r)
                produces = r.produces()

            headers = {}
            if cache:
                headers['Cache-Control'] = cache

            @wraps(fn)
            def wrapper(*args, **kwargs):
                try:
                    self.set_user(None)
                    args = [p.extract() for p in parameters]
                    req = flask.request
                    if dump:
                        msg = dict(
                            function=fn.__name__,
                            url=req.url,
                            **req.headers)
                        self.logger.debug(msg)
                    kwargs = dict((k, v) for k, v in req.args.items()
                                  if k not in fn.__code__.co_varnames) if (fn.__code__.co_flags & 8) else {}
                    try:
                        if 'uuid' not in flask.g:
                            flask.g.uuid = uuid.uuid4()
                        time_start = time.clock()
                        res = fn(*args, **kwargs)
                        if self.statsd:
                            time_end = time.clock()
                            self.statsd.timing(op + '.request', time_end - time_start)
                    except errors.Unauthorized as e:
                        if has_browser():
                            res = [[u['authorizationUrl'] for u in v.values() if u['type'] == 'oauth2'] for v in security]
                            res = [x[0] for x in res if len(x) > 0]
                            if len(res) > 0:
                                return flask.redirect(
                                    location=res[0] + '&redirect=' + urllib.parse.quote(flask.request.url),
                                    code=status.TEMPORARY_REDIRECT)
                        raise e
                    except errors.BaseException as e:
                        raise e
                    except Exception as e:
                        raise errors.InternalServerError(e)

                    if res is None:
                        return flask.Response(status=status.NO_CONTENT)
                    if isinstance(res, flask.Response):
                        return res
                    kind = req.accept_mimetypes.best_match(produces)
                    if req.method == 'POST' and isinstance(res, Resource):
                        return flask.Response(status=status.CREATED, headers={'Location': res.uri})
                    headers['x-content-class'] = type(res).__name__
                    if req.method == 'HEAD':
                        return flask.Response(mimetype=kind, status=status.OK, headers=headers)
                    return flask.Response(self.convert(kind, res), mimetype=kind, status=status.OK, headers=headers)
                except errors.BaseException as e:
                    msg = support.extract_call_info(fn, args, kwargs)
                    self.logger.exception(msg)
                    e.put(operationId=op, path=path)
                    raise e

            args = dict(operationId=op, tags=tags, produces=produces, description=desc,
                        parameters=[p.json() for p in parameters if not p.hidden],
                        responses=dict((str(v.code().value), v.json()) for v in resp)
                        )
            if security:
                args['security'] = security
            for p in parameters:
                if p.location == 'body':
                    args['consumes'] = p.consumes()
                    break

            wrapper.__doc__ = '{0}\n---\n{1}'.format(summary, yaml.dump(args, default_flow_style=False))
            endpoint = options.pop('endpoint', None)
            self.flask.add_url_rule(self.base + path, endpoint, wrapper, **options)
            return fn

        return decorator

    def oauth2(self, security, authorizationUrl, flow='implicit', tokenUrl=None, refreshUrl=None, required=True):
        support.check_param(security, str, True)
        support.check_param(authorizationUrl, str, True)
        support.check_param(tokenUrl, str, False)
        support.check_param(refreshUrl, str, False)
        support.check_param(flow, ['implicit', 'password', 'clientCredentials', 'authorizationCode'], True)
        if security not in self.securities:
            self.securities[security] = dict(flow=flow, authorizationUrl=authorizationUrl, type='oauth2', scopes={})

        def f(name=None, **args):
            self.securities[security]['scopes'].update(args)
            return JWTHeader(name=name, security=security, keys=list(args.keys()), service=self, required=required)
        return f

    def basic(self, security, required=True):
        if security not in self.securities:
            res = dict(type='basic', scopes={})
            self.securities[security] = res

        def f(name=None, **args):
            self.securities[security]['scopes'].update(args)
            return BasicHeader(name=name, security=security, keys=list(args.keys()), service=self, required=required)
        return f

    def api_key(self, security, required=True):
        if security not in self.securities:
            res = dict(type='apiKey', scopes={})
            self.securities[security] = res

        def f(name=None, **args):
            self.securities[security]['scopes'].update(args)
            return ApiKeyHeader(name=name, security=security, keys=list(args.keys()), service=self, required=required)
        return f

    def add_user(self, username, password):
        self.passwords[username] = password

    def add_key(self, api_key):
        self.api_keys.add(api_key)

    def set_user(self, user):
        if self.log_filter:
            self.log_filter.data.user = user
