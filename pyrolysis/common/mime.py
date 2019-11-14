import io, sys
from collections import namedtuple, Mapping, Iterable
from json import JSONEncoder

import marshmallow
import requests
import base64
from datetime import date, datetime
from enum import Enum

from pyrolysis.common.support import keep


application = namedtuple('mimetype', ['pickle', 'msgpack', 'json', 'csv', 'xml', 'text'])(
    text="application/text",
    json="application/json",
    csv="application/csv",
    xml="application/xml",
    msgpack="application/msgpack",
    pickle="application/pickle"
)

text = namedtuple('mimetype', ['csv', 'xml', 'plain'])(
    plain="text/plain",
    csv="text/csv",
    xml="text/xml"
)

mimetypes = list(application) + list(text)
from pyrolysis.common import pandas_df_type
from pyrolysis.common import errors


class JSONEncoder2(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
        if isinstance(o, type):
            return o.__module__ + '.' + o.__name__
        if isinstance(o, Enum):
            return o.name
        return JSONEncoder.default(self, o)


class Converter:
    schemas = {}

    def register(self, cls, mapper):
        self.schemas[cls.__name__] = mapper()

    def schema_convert(self, data, checker=None):
        if isinstance(data, Iterable) and not isinstance(data, Mapping) and not isinstance(data, str):
            return [self.schema_convert(x) for x in data]
        cls = type(data).__name__
        if cls in self.schemas:
            try:
                data = self.schemas[cls].dump(data)
            except marshmallow.exceptions.ValidationError as e:
                raise errors.BadRequest(errors=e.data, status='conflict')
        if checker:
            checker(data)
        return data

    def schema_revert(self, data, cls, checker=None):
        if isinstance(data, Iterable) and not isinstance(data, Mapping) and not isinstance(data, str):
            return [self.schema_revert(x, cls, checker) for x in data]
        if isinstance(data, str) and cls != 'str' and cls != str:
            data = self.str_revert(data, cls)
        if checker:
            checker(data)
        if isinstance(cls, type):
            cls = cls.__name__
        if cls in self.schemas:
            try:
                data = self.schemas[cls].load(data)
            except marshmallow.exceptions.ValidationError as e:
                raise errors.BadRequest(errors=e.data, status='conflict')
        return data

    def str_convert(self, val, **kw):
        if val is None:
            return ''
        elif isinstance(val, str):
            return val
        elif isinstance(val, bytes):
            return base64.b64encode(val)
        elif isinstance(val, bytearray):
            return base64.b64encode(val)
        elif isinstance(val, date):
            return val.isoformat()
        elif isinstance(val, datetime):
            return val.isoformat()
        elif isinstance(val, int):
            return str(val)
        elif isinstance(val, float):
            return str(val)
        elif isinstance(val, Enum):
            return val.name
        elif isinstance(val, type):
            return val.__module__ + '.' + val.__name__
        elif isinstance(val, bool):
            return 'true' if val else 'false'
        elif isinstance(val, Mapping):
            raise errors.BadRequest(type=type(val), status='unknown')
        elif isinstance(val, Iterable):
            return ','.join(self.str_convert(x) for x in val)
        raise errors.BadRequest(type=type(val), status='unknown')

    def str_revert(self, val, cls, many=False, **kw):
        if val is None:
            return val
        if type(val) == cls:
            return val
        if isinstance(val, requests.Response):
            val = val.text
        if isinstance(val, bytes):
            val = val.decode(**kw)
        if len(val) == 0:
            return None
        if many:
            return [self.str_revert(x, cls, False, **kw) for x in val.split(',')]
        try:
            if cls == 'date' or cls == date:
                return datetime.strptime(val, '%Y-%m-%d').date()
            elif cls == 'datetime' or cls == datetime:
                return datetime.strptime(val, '%Y-%m-%dT%H:%M:%S')
            elif cls == 'int' or cls == int:
                return int(val)
            elif cls == 'float' or cls == float:
                return float(val)
            elif cls == 'str' or cls == str:
                return val
            elif cls == 'type' or cls == type:
                p = val.rindex('.')
                return getattr(sys.modules[val[:p]], val[p+1:])
            elif cls == 'bytes' or cls == bytes:
                return base64.b64decode(val)
            elif cls == 'bytearray' or cls == bytearray:
                return bytearray(base64.b64decode(val))
            elif cls == 'bool' or cls == bool:
                val = val.lower()
                if val in ['true', 'false']:
                    return val == 'true'
            elif issubclass(cls, Enum):
                return cls[val]
        except Exception:
            raise errors.BadRequest(val=val, type=cls, status='conflict')
        raise errors.BadRequest(val=val, type=cls, status='unknown')

    def csv_convert(self, val, checker=None, **kw):
        if type(val) != list:
            val = [val]
        elif len(val) == 0:
            return ''
        import csv
        buf = io.StringIO()
        if isinstance(val, pandas_df_type):
            val.to_csv(buf, **keep(kw, []))
        else:
            val = self.schema_convert(val, checker)
            t = val[0]
            if isinstance(t, Mapping):
                if checker:
                    checker(val)
                w = csv.DictWriter(buf, sorted(t.keys()), lineterminator='\n', **keep(kw, []))
                w.writeheader()
                w.writerows(val)
            elif isinstance(t, Iterable):
                if checker:
                    checker(val)
                w = csv.writer(buf, lineterminator='\n', **keep(kw, []))
                w.writerows(val)
            else:
                raise errors.BadRequest(type=t.__name__, status='unknown')
        return buf.getvalue()

    def csv_revert(self, val, cls=dict, checker=None, **kw):
        if cls == pandas_df_type or cls == pandas_df_type.__name__:
            import pandas
            if isinstance(val, requests.Response):
                return pandas.read_csv(val.content, **keep(kw, []))
            elif isinstance(val, bytes):
                return pandas.read_csv(io.BytesIO(val), **keep(kw, []))
            else:
                return pandas.read_csv(io.StringIO(val), **keep(kw, []))
        import csv
        if isinstance(val, requests.Response):
            inp = val.iter_content()
        elif isinstance(val, bytes):
            inp = io.StringIO(val.decode(**keep(kw, [])))
        else:
            inp = io.StringIO(val)
        data = list(dict(x) for x in csv.DictReader(inp, delimiter=',', **kw))
        data = self.schema_revert(data, cls, checker=checker)
        return data

    def xml_convert(self, val, checker=None, **kw):
        from xml.dom import minidom
        doc = minidom.getDOMImplementation().createDocument(None, "some_tag", None)

        def convert_node(n, e):
            if isinstance(n, Mapping):
                for k, v in n.items():
                    convert_node(v, doc.createElement(k))
                    if isinstance(v, list):
                        for v2 in v:
                            e2 = doc.createElement(k)
                            if type(v2) not in [str,dict]:
                                e2.setAttribute('type', type(v2).__name__)
                            convert_node(v2, e2)
                            e.appendChild(e2)
                    else:
                        e2 = doc.createElement(k)
                        if type(v) not in [str, dict]:
                            e2.setAttribute('type', type(v).__name__)
                        convert_node(v, e2)
                        e.appendChild(e2)
            else:
                e.appendChild(doc.createTextNode(self.str_convert(n)))

        clname = type(val).__name__
        val = self.schema_convert(val, checker=checker)

        e = doc.createElement(clname)
        if val is list:
            for v2 in val:
                e2 = doc.createElement(type(v2).__name__)
                convert_node(v2, e2)
                e.appendChild(e2)
        else:
            convert_node(val, e)
        return e.toxml()

    def xml_revert(self, val, cls, checker=None, **kw):
        from xml.dom import minidom

        def revert_node(n):
            res = {}
            txt = ''
            for c in n.childNodes:
                if c.nodeType == c.TEXT_NODE:
                    txt += c.data
                else:
                    e = revert_node(c)
                    if c.hasAttribute('type'):
                        e = self.str_revert(e, c.getAttribute('type'), False)
                    if c.nodeName in res:
                        v = res[c.nodeName]
                        if type(v) == list:
                            v.append(e)
                        else:
                            res[c.nodeName] = [v, e]
                    else:
                        res[c.nodeName] = e
            if len(res) > 0:
                return res
            return txt

        if isinstance(val, requests.Response):
            val = val.text
        elif isinstance(val, bytes):
            val = val.decode(**keep(kw, []))
        elif not isinstance(val, str):
            raise errors.BadRequest(type=type(val).__name__, status='unknown')

        res = revert_node(minidom.parse(io.StringIO(val)).firstChild)

        return self.schema_revert(res, cls, checker=checker)

    def msgpack_convert(self, val, checker=None, **kw):
        if pandas_df_type and isinstance(val, pandas_df_type):
            buf = io.BytesIO()
            val.to_msgpack(buf, **keep(kw, []))
            return buf.getvalue()
        val = self.schema_convert(val, checker=checker)
        import msgpack
        return msgpack.dumps(val, **keep(kw, []))


    def msgpack_revert(self, val, cls=dict, checker=None, **kw):
        if cls == pandas_df_type.__name__ or cls == pandas_df_type:
            import pandas
            if isinstance(val, requests.Response):
                return pandas.read_msgpack(val.content, **keep(kw, []))
            else:
                return pandas.read_msgpack(io.BytesIO(val), **keep(kw, []))
        if isinstance(val, requests.Response):
            val = val.content
        import msgpack
        val = msgpack.loads(val, **keep(kw, []))
        val = self.schema_revert(val, cls, checker=checker)
        return val

    def json_convert(self, val, checker=None, **kw):
        import json
        if pandas_df_type and isinstance(val, pandas_df_type):
            buf = io.StringIO()
            val.to_json(buf, **keep(kw, []))
            res = buf.getvalue()
            return res
        val = self.schema_convert(val, checker=checker)
        return json.dumps(val, cls=JSONEncoder2, **keep(kw, []))

    def json_revert(self, val, cls=dict, checker=None, **kw):
        if cls == pandas_df_type.__name__ or cls == pandas_df_type:
            import pandas
            if isinstance(val, requests.Response):
                return pandas.read_json(val.content, **keep(kw, []))
            elif isinstance(val, bytes):
                return pandas.read_json(io.BytesIO(val), **keep(kw, []))
            elif isinstance(val, str):
                return pandas.read_json(io.StringIO(val), **keep(kw, []))
            else:
                raise errors.BadRequest(type=type(val).__name__, status='unknown')
        if isinstance(val, requests.Response):
            val = val.text
        import json
        val = json.loads(val, **keep(kw, ['encoding']))
        val = self.schema_revert(val, cls, checker=checker)
        return val

    def pickle_convert(self, val, checker=None, **kw):
        val = self.schema_convert(val, checker)
        import pickle
        return pickle.dumps(val, **keep(kw, []))

    def pickle_revert(self, val, cls=dict, checker=None, **kw):
        if isinstance(val, requests.Response):
            val = val.text
        import pickle
        val = pickle.loads(val, **keep(kw, []))
        val = self.schema_revert(val, cls, checker=checker)
        return val

    def convert(self, ct, val, **kw):
        if ct == application.json:
            return self.json_convert(val, **kw)
        if ct == application.xml or ct == text.xml:
            return self.xml_convert(val, **kw)
        if ct == application.pickle:
            return self.pickle_convert(val, **kw)
        if ct == application.msgpack:
            return self.msgpack_convert(val, **kw)
        if ct == application.csv or ct == text.csv:
            return self.csv_convert(val, **kw)
        if ct == application.text or ct == text.plain:
            return self.str_convert(val, **kw)
        raise errors.BadRequest()

    def revert(self, ct, val, **kw):
        if ct == application.json:
            return self.json_revert(val, **kw)
        if ct == application.xml or ct == text.xml:
            return self.xml_revert(val, **kw)
        if ct == application.pickle:
            return self.pickle_revert(val, **kw)
        if ct == application.msgpack:
            return self.msgpack_revert(val, **kw)
        if ct == application.csv or ct == text.csv:
            return self.csv_revert(val, **kw)
        if ct == application.text or ct == text.plain:
            return self.str_revert(val, **kw)
        raise errors.BadRequest()
