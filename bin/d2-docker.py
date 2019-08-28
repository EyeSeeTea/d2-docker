#!/usr/bin/env python
import sys
import argparse

import utils
from commands import start, logs, stop, commit, push, copy, export, import_, list_, run_sql

COMMAND_MODULES = [start, logs, stop, commit, push, copy, export, import_, list_, run_sql]


def get_parser():
    parser = argparse.ArgumentParser(prog="d2-docker")
    parser.add_argument(
        "--dhis2-db-docker-directory",
        metavar="DIRECTORY",
        type=str,
        help="Directory container dhis2-db docker source",
    )
    parser.add_argument(
        "--log-level",
        metavar="NOTSET | DEBUG | INFO | WARNING | ERROR | CRITICAL",
        default="INFO",
        type=str,
        help="Run command with the given log level",
    )
    subparsers = parser.add_subparsers(help="Subcommands", dest="command")

    for command_module in COMMAND_MODULES:
        name = getattr(command_module, "NAME", None) or command_module.__name__.split(".")[-1]
        subparser = subparsers.add_parser(name, help=command_module.DESCRIPTION)
        command_module.setup(subparser)
        subparser.set_defaults(func=command_module.run)

    return parser


def main(argv):
    parser = get_parser()
    args = parser.parse_args(argv)
    utils.logger.setLevel(args.log_level)

    if not getattr(args, "func", None):
        parser.print_usage()
        return 1
    else:
        try:
            return args.func(args)
        except utils.D2DockerError as exc:
            print(str(exc), file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
