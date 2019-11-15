import threading
import flask
import requests
import time


def start_server(app: flask.Flask, port=5000):
    @app.route('/shutdown', methods=['POST'])
    def shutdown():
        func = flask.request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        return "OK", 200
    app.run(port=port, host='0.0.0.0', debug=True, use_reloader=False)


def stop_server(port=5000):
    requests.post('http://localhost:{}/shutdown'.format(port))
    time.sleep(0.1)


def start_server_background(app: flask.Flask, port=5000):
    server_thread = threading.Thread(target=start_server, args=(app, port))
    server_thread.start()
    time.sleep(0.1)
