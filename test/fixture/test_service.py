from enum import Enum, auto
import flask
from flask import g
from pandas import DataFrame
from dataclasses import dataclass, field

from pyrolysis.server.parameter import Header
from pyrolysis.server.security import BasicHeader, ApiKeyHeader
from pyrolysis.server.service import ServerService


class MyEnum(Enum):
    ONE = auto()
    TWO = auto()
    THREE = auto()


@dataclass
class TestServerObject:
    name: str = field()
    id: int = field()


class BasicSecurity(BasicHeader):
    def fetch_roles(self, username, password):
        if username == 'user' and password == 'password':
            return ['authenticated']
        return []


class ApiKeySecurity(ApiKeyHeader):
    def fetch_roles(self, key):
        if key == 'azerty':
            return ['admin']
        return []


flsk = flask.Flask('test')
app = ServerService(flsk)
app.register(TestServerObject)
basic = BasicSecurity(name='test_sec1')
authenticated = basic.add_role("authenticated")
apikey = ApiKeySecurity(name='test_sec2', header='x-api-key')
admin = apikey.add_role("admin")


@app.get('/test/<p>')
def test_path(p: int = 1) -> int:
    """
    Example 1 for a unit test

    :param p: example of description
    :return: return data
    """
    return p


@app.get('/test2')
def test_query(p: int = 1) -> int:
    """
    Example 2 for a unit test
    :param p: example of description
    :return: return data
    """
    return p


@app.get(
    '/test3',
    parameters=[
        Header(description='example of description')
    ]
)
def test_header(p: int = 1) -> int:
    """
    Example 3 for a unit test
    :returns test
    :return: return test
    """
    return p


@app.post('/test4')
def test_body(p: dict) -> dict:
    """
    Example 4 for a unit test

    :param p: example of description
    """
    return p


@app.get('/test5', roles=authenticated)
def test_security() -> str:
    """Example 5 for a unit test"""
    return g.username


@app.get('/test5b', roles=admin)
def test_security2() -> str:
    """Example 5 for a unit test"""
    return g.apikey


@app.get('/test6')
def test_exception() -> None:
    """Example 6 for a unit test"""
    raise Exception('Problem')


@app.get('/test7')
def test_enum(p: MyEnum = MyEnum.ONE) -> MyEnum:
    """
    Example 7 for a unit test
    :param p: example of description
    :return: return data
    """
    return p


@app.post('/test8')
def test_object(p: TestServerObject) -> TestServerObject:
    """
    Example 8 for a unit test
    :param p: example of description
    :return: return data
    """
    return p


@app.post('/test9')
def test_dataframe(p: DataFrame) -> DataFrame:
    """
    Example 8 for a unit test
    :param p: example of description
    :return: return data
    """
    return p
