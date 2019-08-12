import subprocess


def run(command_parts):
    result = subprocess.run(command_parts, check=True)
