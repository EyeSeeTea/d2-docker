import os
import base64
from d2_docker.commands import list_
from flask import jsonify
from dotenv import dotenv_values


class Struct(object):
    def __init__(self, dictionary):
        self.__dict__.update(dictionary)

    def __getattr__(self, item):
        return None

    def __repr__(self):
        pairs = ", ".join("{}={}".format(k, repr(v)) for (k, v) in self.__dict__.items())
        return "Struct(" + pairs + ")"


def get_args_from_request(request):
    body = request.get_json()
    args = Struct(body)
    return args


def get_auth_headers(user, password):
    encoded_auth = base64.b64encode((user + ":" + password).encode()).decode()
    return {"Authorization": "Basic " + encoded_auth}


def get_container(name):
    containers = list_.get_containers()
    return next((c for c in containers if c["name"] == name), None)


def success():
    return jsonify(dict(status="SUCCESS"))


def server_error(message, status=500):
    body = jsonify(dict(status="ERROR", error=message))
    return (body, status)


def get_config():
    return {
        **dotenv_values(".flaskenv", verbose=True),
        **dotenv_values(".flaskenv.secret", verbose=True),
        **os.environ,
    }
