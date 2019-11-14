import unittest
import time
import os


class Toto:
    mod = 0

    def f(self, x):
        return x * x + self.mod


class TestCache(unittest.TestCase):

    def test_lru_caching(self):
        from pyrolysis.common.cache import memory_cache
        x = Toto()
        cached = memory_cache(x, 5, 1)
        x.mod = 0
        self.assertEqual(cached.f(2), 4)
        # cache effect
        x.mod = 1
        self.assertEqual(cached.f(2), 4)
        # cache expired
        time.sleep(2)
        self.assertEqual(cached.f(2), 5)

    def test_disk_caching(self):
        from pyrolysis.common.cache import disk_cache
        filename = "c:\\tmp\\cache.shelve"
        if os.path.exists(filename):
            os.remove(filename)
        x = Toto()
        cached = disk_cache(x, filename)

        x.mod = 0
        self.assertEqual(cached.f(2), 4)
        # cache effect
        x.mod = 1
        self.assertEqual(cached.f(2), 4)

    def test_lru_caching_func(self):
        from pyrolysis.common.cache import caching
        import cachetools
        c = cachetools.TTLCache(5, 1)
        mod = 0

        @caching(c)
        def f(x):
            return x * x + mod

        self.assertEqual(f(2), 4)
        # cache effect
        mod = 1
        self.assertEqual(f(2), 4)
        # cache expired
        time.sleep(2)
        self.assertEqual(f(2), 5)


if __name__ == '__main__':
    unittest.main()
