import base64


def keep(obj, fields):
    return dict((k, v) for k, v in obj.items() if k in fields)


from pyrolysis.common import errors


def check_param(val, type, mandatory):
    if val is None:
        if mandatory:
            raise errors.BadRequest(status='missing')
    elif isinstance(type, list):
        if val not in type:
            raise errors.BadRequest(val=val, enum=type, status='unknown')
    elif not isinstance(val, type):
        raise errors.BadRequest(type=type.__name__, val=type(val).__name__, status='conflict')


def decode_base64(base64_encoded_string):
    """
    Decode base64, padding being optional.

    :param base64_encoded_string: Base64 data as an ASCII byte string
    :returns: The decoded byte string.
    """
    missing_padding = len(base64_encoded_string) % 4
    if missing_padding != 0:
        base64_encoded_string += '=' * (4 - missing_padding)
    return base64.b64decode(base64_encoded_string)


def purge(val):
    if isinstance(val, set):
        return set(purge(x) for x in val if x is not None)
    elif isinstance(val, list):
        return list(purge(x) for x in val if x is not None)
    elif isinstance(val, tuple):
        return tuple(purge(x) for x in val if x is not None)
    elif isinstance(val, dict):
        return dict((k, purge(v)) for k, v in val.items() if v is not None)
    return val


def combine(*args):
    res = {}
    for a in args:
        res.update(a)
    return res


def decode_contenttype(v):
    if v is None:
        raise ValueError('Content-Type is missing')
    parts = v.split(';')
    if len(parts) == 1:
        return parts[0].strip(), 'UTF-8'
    data = parts[1].split('=')
    if data[0].strip() != 'charset':
        return parts[0].strip(), 'UTF-8'
    return parts[0].strip(), data[1].strip()


def extract_call_info(func, func_args, func_kwargs):
    defaults = func.__defaults__ or ()
    args = {}
    kwargs = dict(func_kwargs)
    msg = {'name': func.__name__, 'module': func.__module__, 'args': args}
    nb = func.__code__.co_argcount
    j = 0
    for i in range(nb):
        name = func.__code__.co_varnames[i]
        if i < len(func_args):
            args[name] = repr(func_args[i])
        elif name in kwargs:
            args[name] = repr(kwargs[name])
            del kwargs[name]
        else:
            args[name] = repr(defaults[j])
            j += 1
    if kwargs:
        args['kwargs'] = dict((k, repr(v)) for k, v in kwargs.items())
    if len(func_args) > nb:
        args['args'] = [repr(x) for x in func_args[nb:]]
    return msg


def call_signature(func, args, kwargs):
    return '{}({},{})'.format(func,
                              ','.join(repr(x) for x in args),
                              ','.join(k + '=' + repr(v) for k, v in kwargs.items()))
