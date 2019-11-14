import unittest
from pyrolysis.common.dict_object import DictObject


def f(x):
    return x


class TestDictObject(unittest.TestCase):
    def test_call(self):
        a = DictObject({'g': f})
        self.assertEquals(a.g(1), 1)


if __name__ == '__main__':
    unittest.main()
