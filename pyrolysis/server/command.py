import threading
import flask
import requests
import time


def start_server(app, port=5000):
    @app.post('/shutdown')
    def shutdown():
        func = flask.request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        return "OK", 200
    app.flask.run(port=port, host='0.0.0.0', debug=True, use_reloader=False)


def stop_server(port=5000):
    requests.post('http://localhost:{}/shutdown'.format(port))
    time.sleep(0.1)


def start_server_background(app, port=5000):
    server_thread = threading.Thread(target=start_server, args=(app, port))
    server_thread.start()
    time.sleep(0.1)


def main(args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='port to listen to', default=7501, type=int)
    options = parser.parse_args(args)
    start_server(options.port)
