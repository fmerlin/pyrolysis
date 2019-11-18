from functools import wraps

from pyrolysis.common.support import call_signature


class CacheObject:
    def __init__(self, proxy, cache):
        self.proxy = proxy
        self.cache = cache

    def __getattr__(self, item):
        def f(*args, **kwargs):
            key = call_signature(item, args, kwargs)
            if key in self.cache:
                return self.cache[key]
            func = getattr(self.proxy, item)
            res = func(*args, **kwargs)
            self.cache[key] = res
            return res
        return f


def caching(cache=None):
    if cache is None:
        cache = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args,**kwargs):
            key = call_signature(func.__name__, args, kwargs)
            if key in cache:
                return cache[key]
            res = func(*args, **kwargs)
            cache[key] = res
            return res
        return wrapper
    return decorator


def memory_cache(proxy, size, ttl):
    import cachetools
    return CacheObject(proxy, cachetools.TTLCache(size, ttl))


def disk_cache(proxy, filename):
    import shelve
    return CacheObject(proxy, shelve.open(filename))


def redis_cache(proxy, host='localhost', port=6379, db=0):
    import redis
    return CacheObject(proxy, redis.Redis(host=host, port=port, db=db))
