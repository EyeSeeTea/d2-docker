from d2_docker.api import main

DESCRIPTION = "d2-docker API"


def setup(parser):
    subparsers = parser.add_subparsers(dest="api_command")
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--host", type=str, help="Listen host")
    start_parser.add_argument("-p", "--port", type=int, help="Listen port")


def run(args):
    if args.api_command == "start":
        main.run(args)
    elif args.api_command == "stop":
        print("stop")
