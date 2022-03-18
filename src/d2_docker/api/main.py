from flask import Flask, json, request, render_template
from collections import namedtuple

api = Flask(__name__)

class Struct(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, item):
        return None

@api.route('/instances', methods=['GET'])
def get_instances():
    from d2_docker.commands.list_ import get_running_containers, get_images_info
    running_containers = get_running_containers()
    images_info = get_images_info(running_containers)
    sorted_values = sorted(images_info, key=lambda val: val["port"] or 1e9)
    containers = list(val for val in sorted_values)
    return json.dumps({"containers": containers})

@api.route('/instances/stop', methods=['POST'])
def stop_instance():
    from d2_docker.commands.stop import run
    body = request.get_json()
    image_name = body["image"]
    get_args = namedtuple("args", ["image"])
    args = get_args(image=image_name)
    run(args)
    return json.dumps({"status": "ok"})

@api.route('/instances/start', methods=['POST'])
def start_instance():
    from d2_docker.commands.start import start
    body = request.get_json()
    image_name = body["image"]
    args = Struct(port=body.get("port"), detach=True)
    start(args, image_name)
    return json.dumps({"status": "ok"})

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
