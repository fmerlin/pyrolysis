import unittest
import requests
from pandas import DataFrame

from pyrolysis.common import errors
from pyrolysis.server import command
from pyrolysis.client import service
import fixture.test_service as tst


class TestService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command.start_server_background(tst.flsk, 4000)
        cls.serv = service.ClientService('http://localhost:4000', username='user', password='password', api_key='azerty').build()

    @classmethod
    def tearDownClass(cls):
        command.stop_server(4000)

    def test_path(self):
        res = self.serv.test_path(1)
        self.assertEqual(res, 1)

    def test_query(self):
        res = self.serv.test_query(1)
        self.assertEqual(res, 1)

    def test_header(self):
        res = self.serv.test_header(1)
        self.assertEqual(res, 1)

    def test_body(self):
        res = self.serv.test_body({'x': 1})
        self.assertEqual(res, {'x': 1})

    def test_security(self):
        res = self.serv.test_security()
        self.assertEqual(res, 'user')

    def test_security2(self):
        res = self.serv.test_security2()
        self.assertEqual(res, 'azerty')

    def test_client_exception(self):
        resp = requests.get('http://localhost:4000/test/hello')
        self.assertEqual(resp.status_code, 400)

    def test_client_exception_2(self):
        try:
            self.serv.test_header('hello')
            self.fail()
        except errors.BadRequest:
            pass

    def test_server_exception(self):
        try:
            self.serv.test_exception()
            self.fail()
        except errors.InternalServerError:
            pass

    def test_enum(self):
        res = self.serv.test_enum(tst.MyEnum.TWO, _return=tst.MyEnum)
        self.assertEqual(res, tst.MyEnum.TWO)

    def test_object(self):
        a = tst.TestServerObject('a', 1)
        res = self.serv.test_object(a, _return=tst.TestServerObject)
        self.assertEqual(res, a)

    def test_dataframe(self):
        a = DataFrame(data=[[1, 2], [3, 4]], columns=['a', 'b'])
        res = self.serv.test_dataframe(a, _return=DataFrame)
        self.assertTrue(a.equals(res))


if __name__ == '__main__':
    unittest.main()
