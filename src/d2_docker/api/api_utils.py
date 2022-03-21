import sys
import io
import contextlib
from flask import abort


from d2_docker.commands import list_

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

def get_container(name):
    containers = list_.get_containers()
    return next((c for c in containers if c["name"] == name), None)

