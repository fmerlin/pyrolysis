## Pyrolysis is a simple way to create and use REST Apis using python 3 type system


server example:

    flsk = flask.Flask('test')
    app = Service(flsk, base='/my_service')

    @app.get('/test/<p>')
    def test_path(p: int=1) -> int:
        """
        Example 1 for a unit test
    
        :param p: example of description
        :return: return data
        """
        return p

    start_server(app, 5000)

client example:

    serv = pyrolysis.server.route.SwaggerService('http://localhost:5000/my_service').load()
    res = serv.test_path(2)

The service will:

* cast and check all the parameters to know if
    - they have the right type
    - they are mandatory

* handle the content type, complex types use marshmallow

* encoding is automatically adapted

* authenticate if necessary

* swagger 2 definition is generated and based on the method signature and docstring

* type annotation is optional

* pandas dataframe can be returned
