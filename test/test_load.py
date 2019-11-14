import unittest
from pyrolysis.client import service


class TestService(unittest.TestCase):
    def test_petshop(self):
        guru5 = service.SwaggerService()
        guru5.load(file='fixture/petshop-swagger.json')
        self.assertTrue(guru5.is_compatible_with(guru5))


if __name__ == '__main__':
    unittest.main()
