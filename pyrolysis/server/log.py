import threading

import flask
import logging


class RequestFilter(logging.Filter):
    data = threading.local()

    # Put request info on log record
    def filter(self, record):
        headers = flask.request.headers
        record.host = headers.get("x-session-host", '')
        record.login = headers.get("x-session-login", '')
        record.session = headers.get("x-session-start", '')
        record.request = headers.get("x-session-request", '')
        record.uuid = flask.g.get('uuid', '')
        record.user = self.data.user
        return True


def setup_request_filter(service):
    f = RequestFilter()
    for logger_name in logging.getLogger().manager.loggerDict.keys():
        logging.getLogger(logger_name).addFilter(f)
    service.log_filter = f
