from collections import namedtuple

from flask import Flask, json, request, render_template

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

#@api.route('/cors/...', methods=['GET'])
#def cors():
#    return request(*args, cors, authentication)

def run(args):
    api.run(
        host=args.host or "0.0.0.0",
        port=args.port or 5000
    )

if __name__ == '__main__':
    run()
