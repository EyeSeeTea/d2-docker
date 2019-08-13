#!/usr/bin/env python3
import sys
import argparse
import logging

from commands import start, logs, stop, commit
from utils import D2DockerError

COMMAND_MODULES = [start, logs, stop, commit]


def get_parser():
    parser = argparse.ArgumentParser(prog="d2-docker")
    # parser.add_argument('--foo', action='store_true', help='foo help')
    subparsers = parser.add_subparsers(help="Subcommands", dest="command")

    for command_module in COMMAND_MODULES:
        name = command_module.__name__.split(".")[-1]
        subparser = subparsers.add_parser(name, help=command_module.DESCRIPTION)
        command_module.setup(subparser)
        subparser.set_defaults(func=command_module.run)

    return parser


def main(argv):
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")
    parser = get_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_usage()
        return 1
    else:
        try:
            args.func(args)
        except D2DockerError as exc:
            print(str(exc), file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
