from collections import namedtuple
import requests

from flask import Flask, json, request, render_template
from flask import Response, stream_with_context

from d2_docker import utils
from d2_docker.commands import version, list_, start, stop, logs
from .api_utils import get_args_from_request, get_container

utils.logger.setLevel("DEBUG")
api = Flask(__name__)


@api.route('/version', methods=['GET'])
def get_version():
    versions = version.get_versions()
    return json.dumps(versions)

@api.route('/instances', methods=['GET'])
def get_instances():
    containers = list_.get_containers()
    return json.dumps({"containers": containers})

@api.route('/instances/start', methods=['POST'])
def start_instance():
    args = get_args_from_request(request)
    start.run(args)
    container = get_container(args.image)
    return json.dumps(dict(status="SUCCESS", container=container))

@api.route('/instances/stop', methods=['POST'])
def stop_instance():
    args = get_args_from_request(request)
    stop.run(args)
    container = get_container(args.image)
    return json.dumps(dict(status="SUCCESS", container=container))

@api.route('/instances/logs', methods=['POST'])
def logs_instance():
    args = get_args_from_request(request)
    last_logs = logs.get_logs(args)
    return json.dumps(dict(logs=last_logs))

@api.route('/', methods=['GET'])
def landing_page():
    return render_template('index.html')

@api.route('/cors/<path:url>', methods=["GET", "POST", "PUT", "DELETE"])
def proxy(url):
    method = request.method.lower()
    http_request = getattr(requests, method)
    headers = dict((k, v) for (k, v) in dict(request.headers).items() if k != "Host")

    if request.json:
        forward_request = http_request(url, json=request.json, headers=headers)
    elif request.form:
        forward_request = http_request(url, data=request.form.to_dict(), headers=headers)
    else:
        forward_request = http_request(url, headers=headers)

    response = stream_with_context(forward_request.iter_content())
    return Response(response, content_type=request.content_type)


def run(args):
    api.run(
        host=args.host or "0.0.0.0",
        port=args.port or 5000
    )

if __name__ == '__main__':
    run()
