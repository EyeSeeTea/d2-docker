import os
import base64
from datetime import datetime
from d2_docker.commands import list_
from flask import jsonify, Response
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
    return Struct(body)


def get_args_from_query_strings(request):
    return Struct(request.args.to_dict())


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


def stream_response(iterator, mimetype, filename):
    response = Response(iterator, mimetype=mimetype)
    response.headers["Content-Disposition"] = "attachment; filename={}".format(filename)
    return response


def get_timestamp():
    return datetime.today().replace(microsecond=0).isoformat()


def get_from_dotenv(name, directories):
    output = {}
    for directory in directories:
        path1 = os.path.join(directory, name)
        path2 = os.path.expanduser(path1)
        value = dotenv_values(path2, verbose=True)
        output.update(value)
    return output


config = None


def get_config():
    global config
    if config:
        return config

    directories = ["~/.config/d2-docker"]
    config = {
        **get_from_dotenv("flaskenv.secret", directories),
        **os.environ,
    }
    return config
