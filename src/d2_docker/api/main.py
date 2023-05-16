import requests
from codecs import decode

from flask import Flask, jsonify, request
from flask import Response, stream_with_context
from flask_cors import CORS

from werkzeug.exceptions import HTTPException, BadRequest

from d2_docker import utils
from d2_docker.commands import version, list_, start, stop, logs, commit, push, pull, run_sql
from d2_docker.commands import copy, rm
from .api_utils import (
    get_args_from_query_strings,
    get_args_from_request,
    get_container,
    get_timestamp,
    stream_response,
    success,
    server_error,
)
from .api_utils import get_auth_headers, get_config


utils.logger.setLevel("DEBUG")
api = Flask(__name__)
CORS(api)


@api.route("/version", methods=["GET"])
def get_version():
    versions = version.get_versions()
    return jsonify(versions)


@api.route("/instances", methods=["GET"])
def get_instances():
    containers = list_.get_containers()
    return jsonify({"containers": containers})


@api.route("/instances/start", methods=["POST"])
def start_instance():
    args = get_args_from_request(request)
    start.run(args)
    container = get_container(args.image)
    return jsonify(dict(status="SUCCESS", container=container))


@api.route("/instances/stop", methods=["POST"])
def stop_instance():
    args = get_args_from_request(request)
    stop.run(args)
    container = get_container(args.image)
    return jsonify(dict(status="SUCCESS", container=container))


@api.route("/instances/logs", methods=["GET"])
def logs_instance():
    args = get_args_from_query_strings(request)
    logs_stream = logs.get_stream_logs(args)
    filename = "{}.{}.log".format(args.image, get_timestamp())
    return stream_response(logs_stream, mimetype="text/plain", filename=filename)


@api.route("/instances/db", methods=["GET"])
def dump_db_instance():
    args = get_args_from_query_strings(request)
    db_stream = run_sql.get_stream_db(args.image)
    filename = "{}.{}.sql.gz".format(args.image, get_timestamp())
    return stream_response(db_stream, mimetype="application/gzip", filename=filename)


@api.route("/instances/commit", methods=["POST"])
def commit_instance():
    args = get_args_from_request(request)
    commit.run(args)
    return success()


@api.route("/instances/pull", methods=["POST"])
def pull_instance():
    args = get_args_from_request(request)
    pull.run(args)
    return success()


@api.route("/instances/push", methods=["POST"])
def push_instance():
    args = get_args_from_request(request)
    push.run(args)
    return success()


@api.route("/instances/copy", methods=["POST"])
def copy_instance():
    args = get_args_from_request(request)
    copy.run(args)
    return success()


@api.route("/instances/rm", methods=["POST"])
def rm_instance():
    args = get_args_from_request(request)
    rm.run(args)
    return success()


def get_request_json(request):
    try:
        return request.json
    except BadRequest:
        return None


def proxy_request_to_url(request, url, new_headers=None):
    base_headers = utils.dict_remove(dict(request.headers), "Host")
    headers = utils.dict_merge(base_headers, new_headers or {})
    method = request.method.lower()
    http_request = getattr(requests, method)
    request_json = get_request_json(request)

    if request_json:
        forward_request = http_request(url, json=request_json, headers=headers)
    elif request.form:
        forward_request = http_request(url, data=request.form.to_dict(), headers=headers)
    else:
        forward_request = http_request(url, headers=headers)

    response = stream_with_context(forward_request.iter_content())
    return Response(response, content_type=forward_request.headers.get("Content-Type"))


@api.route("/harbor/<path:url>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(url):
    config = get_config()
    user = config.get("HARBOR_USER")
    password = config.get("HARBOR_PASSWORD")
    if not user or not password:
        return server_error("Harbor auth unset")
    else:
        auth_headers = get_auth_headers(user, password)
        return proxy_request_to_url(request, url, auth_headers)


@api.errorhandler(404)
def not_found_error(_error):
    return server_error("Route not found", status=404)


@api.errorhandler(Exception)
def internal_error(error):
    status = error.code if isinstance(error, HTTPException) else 500
    contents = decode(str(error), "unicode-escape")
    return server_error(contents, status=status)


def run(args):
    get_config()
    api.run(host=args.host or "127.0.0.1", port=args.port or 5000)
