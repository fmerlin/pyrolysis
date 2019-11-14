## Pyrolysis is a simple way to create and use REST Apis using python 3 type system


server code example:

    flsk = flask.Flask('test')
    app = ServerService(flsk, base='/my_service')

    @app.get('/test/<p>')
    def test_add_one(p: int=1) -> int:
        """
        Example 1 for a unit test
    
        :param p: example of description
        :return: return data
        """
        return p + 1

    start_server(app, 5000)

client code example:

    serv = ClientService('http://localhost:5000/my_service')
    serv.load()
    res = serv.test_add_one(2)
    assert(res, 3)

server_code example with marshmallow_dataclass:

    @dataclass
    class TestServerObject:
        name: str = field()
        id: int = field()

    flsk = flask.Flask('test')
    app = ServerService(flsk, base='/my_service')
    app.register(TestServerObject)

    @app.get('/test2')
    def test_obj(p: TestServerObject) -> TestServerObject:
        return p

The service will:

* cast and check all the parameters to know if
    - they have the right type
    - they are mandatory

* handle the content type, complex types use marshmallow:

* encoding is automatically adapted

* authenticate if necessary

* swagger 2 definition is generated and based on the method signature and docstring

* type annotation is optional

* pandas dataframe can be used
