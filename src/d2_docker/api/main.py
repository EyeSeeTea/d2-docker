import base64
import traceback
import os
from collections import namedtuple
import requests
from requests.auth import HTTPBasicAuth

from flask import Flask, jsonify, request, render_template
from flask import Response, stream_with_context
from dotenv import dotenv_values

from d2_docker import utils
from d2_docker.commands import version, list_, start, stop, logs, commit, push, pull
from d2_docker.commands import copy, rm
from .api_utils import get_args_from_request, get_container

utils.logger.setLevel("DEBUG")
api = Flask(__name__)


@api.route('/version', methods=['GET'])
def get_version():
    versions = version.get_versions()
    return jsonify(versions)

@api.route('/instances', methods=['GET'])
def get_instances():
    containers = list_.get_containers()
    return jsonify({"containers": containers})

@api.route('/instances/start', methods=['POST'])
def start_instance():
    args = get_args_from_request(request)
    start.run(args)
    container = get_container(args.image)
    return jsonify(dict(status="SUCCESS", container=container))

@api.route('/instances/stop', methods=['POST'])
def stop_instance():
    args = get_args_from_request(request)
    stop.run(args)
    container = get_container(args.image)
    return jsonify(dict(status="SUCCESS", container=container))

@api.route('/instances/logs', methods=['POST'])
def logs_instance():
    args = get_args_from_request(request)
    last_logs = logs.get_logs(args)
    return jsonify(dict(logs=last_logs))

@api.route('/instances/commit', methods=['POST'])
def commit_instance():
    args = get_args_from_request(request)
    commit.run(args)
    return success()

@api.route('/instances/pull', methods=['POST'])
def pull_instance():
    args = get_args_from_request(request)
    pull.run(args)
    return success()

@api.route('/instances/push', methods=['POST'])
def push_instance():
    args = get_args_from_request(request)
    push.run(args)
    return success()

@api.route('/instances/copy', methods=['POST'])
def copy_instance():
    args = get_args_from_request(request)
    copy.run(args)
    return success()

@api.route('/instances/rm', methods=['POST'])
def rm_instance():
    args = get_args_from_request(request)
    rm.run(args)
    return success()

@api.route('/harbor/<path:url>', methods=["GET", "POST", "PUT", "DELETE"])
def proxy(url):
    method = request.method.lower()
    http_request = getattr(requests, method)
    user = config.get("HARBOR_USER")
    password = config.get("HARBOR_PASSWORD")
    if not user or not password:
        return server_error("Harbor auth unset")

    encoded_auth = base64.b64encode((user + ':' + password).encode()).decode()
    auth_headers = {"Authorization": "Basic " + encoded_auth}
    base_headers = utils.dict_remove(dict(request.headers), "Host")
    headers = utils.dict_merge(base_headers, auth_headers)

    if request.json:
        forward_request = http_request(url, json=request.json, headers=headers)
    elif request.form:
        forward_request = http_request(url, data=request.form.to_dict(), headers=headers)
    else:
        forward_request = http_request(url, headers=headers)

    response = stream_with_context(forward_request.iter_content())
    return Response(response, content_type=request.content_type)

@api.errorhandler(Exception)
def internal_error(error):
    from codecs import encode, decode
    contents = decode(str(error), "unicode-escape")
    return server_error(contents)

def success():
    return jsonify(dict(status="SUCCESS"))

def server_error(message, status=500):
    body = jsonify(dict(status="ERROR", error=message))
    return (body, status)

def get_config():
    return {
        **dotenv_values(".flaskenv"),
        **dotenv_values(".flaskenv.secret"),
        **os.environ,
    }



config = get_config()

def run(args):
    api.run(host=args.host or "0.0.0.0", port=args.port or 5000)

if __name__ == '__main__':
    run()
