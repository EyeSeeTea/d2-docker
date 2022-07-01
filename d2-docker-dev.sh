#!/bin/bash
export PYTHONPATH=src
exec python3 $PYTHONPATH/d2_docker/cli.py "$@"
