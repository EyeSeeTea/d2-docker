"""Request logs: the gateway records selected requests as HAR files (see spec/request-logs.md).

This module validates the rules file for `d2-docker start`, and reads the HAR files for
`d2-docker request-logs`. The gateway side is config/gateway/request_logs*.lua.
"""

import collections
import datetime
import json
import os
import re
from urllib.parse import urlsplit

from d2_docker import utils

KEYS = {"maxAgeDays", "maxBodyBytes", "rules", "comment"}  # top-level keys of the rules file
FIELDS = {"method", "url", "status"}
OPERATORS = {"equal", "notEqual", "match", "notMatch"}

GATEWAY_LOGS_DIR = "/var/log/d2-docker/requests"  # mount point in the gateway (docker-compose.yml)

# Written by config/gateway/request_logs.lua (write_har); keep in sync
FILENAME_RE = re.compile(
    r"^(?P<time>\d{4}-\d\d-\d\d_\d\d_\d\d_\d\d_\d{3})-(?P<method>[A-Z]+)-(?P<status>\d{3})-[0-9a-f]+\.har$"
)
FILENAME_TIME_FORMAT = "%Y-%m-%d_%H_%M_%S_%f"

Entry = collections.namedtuple("Entry", ["path", "time", "method", "status", "user", "url"])


# Rules (d2-docker start)


def prepare_start(args):
    """Check the request logs options of `d2-docker start` and create the logs directory."""
    if bool(args.request_logs_rules) != bool(args.request_logs_dir):
        msg = "--request-logs-rules and --request-logs-dir must be used together"
        raise utils.D2DockerError(msg)
    elif args.request_logs_rules:
        check_rules_file(args.request_logs_rules)
        os.makedirs(args.request_logs_dir, exist_ok=True)


def check_rules_file(path):
    try:
        with open(path) as rules_file:
            check_rules(rules_file.read())
    except (OSError, utils.D2DockerError) as exc:
        raise utils.D2DockerError("Invalid request logs rules ({}): {}".format(path, exc))


def check_rules(text):
    """Validate the rules file text (regexes are validated by the gateway). Raise D2DockerError.

    Twin of rules.parse(text) in config/gateway/request_logs/rules.lua, which validates the rules
    again on gateway start, with the same messages. Shared cases: test/request-logs/rules-cases.json.
    """
    error = utils.D2DockerError

    try:
        data = json.loads(text)
    except ValueError as exc:
        raise error("invalid JSON: {}".format(exc))

    if not isinstance(data, dict):
        raise error("expected an object")

    unknown_keys = set(data) - KEYS
    if unknown_keys:
        raise error("unknown keys: {}".format(", ".join(sorted(unknown_keys))))

    for key in ["maxAgeDays", "maxBodyBytes"]:
        value = data.get(key)
        if value is not None and (type(value) is not int or value <= 0):
            raise error("{} must be a positive integer".format(key))

    rules = data.get("rules", [])
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise error("rules must be a list of objects")

    for rule in rules:
        for field, value in rule.items():
            if field == "comment":
                continue
            elif field not in FIELDS:
                raise error("unknown field: {}".format(field))
            elif not is_valid_condition(field, value):
                msg = "field {}: expected a string or an object with one operator ({})"
                raise error(msg.format(field, ", ".join(sorted(OPERATORS))))


def is_valid_condition(field, value):
    """A condition is an operand (shorthand for equal) or an object with one operator."""
    if is_valid_operand(field, value):
        return True
    elif isinstance(value, dict) and len(value) == 1:
        operator, operand = list(value.items())[0]
        return operator in OPERATORS and is_valid_operand(field, operand)
    else:
        return False


def is_valid_operand(field, value):
    """Operands are strings. Status also accepts integers (i.e. 404)."""
    return isinstance(value, str) or (field == "status" and type(value) is int)


# HAR files (d2-docker request-logs)


class Filters:
    """Filters for the logged requests. Unset (None) filters match everything."""

    def __init__(self, since=None, until=None, method=None, status=None, url=None, user=None):
        self.since = since  # datetime, inclusive
        self.until = until  # datetime, exclusive
        self.method = method and method.upper()
        self.status = status  # regex, matched at the start of the status
        self.url = url  # regex, searched in path + query string
        self.user = user

    def matches_filename(self, time, method, status):
        return not (
            (self.since and time < self.since)
            or (self.until and time >= self.until)
            or (self.method and method != self.method)
            or (self.status and not re.match(self.status, status))
        )

    def matches_request(self, url, user):
        return not ((self.url and not re.search(self.url, url)) or (self.user and user != self.user))


def get_instance_logs_dir(image):
    """Return the host directory where the gateway of a running instance writes request logs."""
    status = utils.get_image_status(image)
    if status["state"] != "running":
        raise utils.D2DockerError("Instance is not running, pass the logs directory")

    template = '{{range .Mounts}}{{if eq .Destination "%s"}}{{.Source}}{{end}}{{end}}'
    gateway = status["containers"]["gateway"]
    result = utils.run(["docker", "inspect", "--format", template % GATEWAY_LOGS_DIR, gateway], capture_output=True)
    directory = result.stdout.decode("utf-8").strip()

    # The gateway mounts the .empty placeholder dir when request logs are disabled
    if not directory or directory == utils.get_absdir_for_docker_volume(None):
        raise utils.D2DockerError("Request logs are not enabled for this instance")
    return directory


def read_entries(directory, filters):
    """Yield the entries matching the filters, sorted by time.

    Time, method and status come from the filename, so only the files that pass
    those filters are opened.
    """
    if not os.path.isdir(directory):
        raise utils.D2DockerError("Not a directory: {}".format(directory))

    for filename in sorted(os.listdir(directory)):
        match = FILENAME_RE.match(filename)
        if not match:
            continue

        time = datetime.datetime.strptime(match.group("time"), FILENAME_TIME_FORMAT)
        method, status = match.group("method"), match.group("status")
        if not filters.matches_filename(time, method, status):
            continue

        path = os.path.join(directory, filename)
        har_entry = read_har_entry(path)
        if not har_entry:
            continue

        url = get_path_and_query(har_entry["request"]["url"])
        user = har_entry.get("_user")
        if filters.matches_request(url, user):
            yield Entry(path=path, time=time, method=method, status=status, user=user, url=url)


def read_har_entry(path):
    """Return the single entry of a HAR file written by the gateway, or None if unreadable."""
    try:
        with open(path) as har_file:
            return json.load(har_file)["log"]["entries"][0]
    except (OSError, ValueError, KeyError, IndexError) as exc:
        utils.logger.warning("Cannot read {}: {}".format(path, exc))
        return None


def get_path_and_query(url):
    parts = urlsplit(url)
    return parts.path + ("?" + parts.query if parts.query else "")


def merge_entries(entries, output_path):
    """Write the entries into a single HAR file. Files are read again here, so listing
    entries does not keep every body (up to maxBodyBytes each) in memory."""
    har = {
        "log": {
            "version": "1.2",
            "creator": {"name": "d2-docker", "version": "1.0"},
            "entries": [read_har_entry(entry.path) for entry in entries],
        }
    }
    with open(output_path, "w") as output:
        json.dump(har, output)
