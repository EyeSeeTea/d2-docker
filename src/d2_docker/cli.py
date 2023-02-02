#!/usr/bin/env python3
import sys
import argparse

from d2_docker import utils
from d2_docker.commands import (
    api,
    start,
    logs,
    stop,
    rm,
    commit,
    push,
    pull,
    copy,
    export,
    import_,
    list_,
    run_sql,
    create,
    upgrade,
    version,
    shell,
)

COMMAND_MODULES = [
    # Implemented in the API:
    version,
    list_,
    start,
    stop,
    logs,
    commit,
    push,
    pull,
    copy,
    rm,
    # Not to be implemented in the API:
    export,
    import_,
    run_sql,
    create,
    upgrade,
    shell,
    api,
]


def get_parser():
    parser = argparse.ArgumentParser(prog="d2-docker")
    parser.add_argument(
        "--dhis2-docker-images-directory",
        metavar="DIRECTORY",
        help="Directory containing dhis2-data docker source code",
    )
    parser.add_argument(
        "--log-level",
        metavar="NOTSET | DEBUG | INFO | WARNING | ERROR | CRITICAL",
        default="INFO",
        help="Run command with the given log level",
    )
    subparsers = parser.add_subparsers(help="Subcommands", dest="command")

    for command_module in COMMAND_MODULES:
        name = getattr(command_module, "NAME", None) or command_module.__name__.split(".")[-1]
        subparser = subparsers.add_parser(name, help=command_module.DESCRIPTION)
        command_module.setup(subparser)
        subparser.set_defaults(func=command_module.run)

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    utils.logger.setLevel(args.log_level.upper())

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
    sys.exit(main())
