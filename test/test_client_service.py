import unittest
import os.path
from pyrolysis.client import service


class TestService(unittest.TestCase):
    def test_petshop(self):
        petshop = service.ClientService(api_key='my_key')
        petshop.load(file=os.path.join(os.path.dirname(__file__), 'fixture', 'petshop-swagger.json'))
        self.assertTrue(petshop.is_compatible_with(petshop))


if __name__ == '__main__':
    unittest.main()
