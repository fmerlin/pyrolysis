from enum import Enum, auto
import flask
from pandas import DataFrame
from dataclasses import dataclass, field

from pyrolysis.server.parameter import Header
from pyrolysis.server.route import ServerService

flsk = flask.Flask('test')
app = ServerService(flsk)


# test_sec = app.oauth2(security='test_sec',
#                      authorizationUrl='')


@dataclass
class TestServerObject:
    name: str = field()
    id: int = field()


app.register(TestServerObject)


class MyEnum(Enum):
    ONE = auto()
    TWO = auto()
    THREE = auto()


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


# @app.get(
#     '/test5',
#     parameters=[test_sec(name='user', my_test2_write='return user')]
# )
# def test_security(user: str) -> str:
#     """Example 5 for a unit test"""
#     return user


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
