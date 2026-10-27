import datetime

from d2_docker import request_logs, utils

DESCRIPTION = "List, filter or merge the request logs (HAR files) of an instance"
NAME = "request-logs"

DATETIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
DATE_FORMAT = "%Y-%m-%d"


def setup(parser):
    parser.add_argument(
        "directory",
        metavar="DIRECTORY",
        nargs="?",
        help="Request logs directory. Default: the directory of the instance given by -i/--image,"
        " or of the single running instance",
    )
    parser.add_argument(
        "-i",
        "--image",
        metavar="IMAGE",
        help="Use the request logs directory of this running dhis2-data image",
    )
    parser.add_argument("--since", metavar="DATETIME", help="From date/time (YYYY-MM-DD[ HH:MM[:SS]])")
    parser.add_argument("--until", metavar="DATETIME", help="Until date/time (YYYY-MM-DD[ HH:MM[:SS]])")
    parser.add_argument("--method", help="Filter by HTTP method")
    parser.add_argument("--status", metavar="REGEX", help="Filter by status (i.e. '5' or '40[13]')")
    parser.add_argument("--url", metavar="REGEX", help="Filter by URL (path + query string)")
    parser.add_argument("--user", help="Filter by username")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--files", action="store_true", help="Only print the paths of the HAR files")
    group.add_argument("--merge", metavar="FILE", help="Merge entries into a single HAR file")


def run(args):
    directory = args.directory or request_logs.get_instance_logs_dir(args.image)
    filters = request_logs.Filters(
        since=parse_datetime(args.since, "--since"),
        until=parse_datetime(args.until, "--until", end_of_day=True),
        method=args.method,
        status=args.status,
        url=args.url,
        user=args.user,
    )
    entries = list(request_logs.read_entries(directory, filters))

    if args.files:
        for entry in entries:
            print(entry.path)
    elif args.merge:
        request_logs.merge_entries(entries, args.merge)
        utils.logger.info("Merged {} entries: {}".format(len(entries), args.merge))
    else:
        print_table(entries)


def parse_datetime(value, option, end_of_day=False):
    """Parse YYYY-MM-DD[ HH:MM[:SS]]. With end_of_day, a date alone means the end of that day
    (so --until=DATE includes the whole day)."""
    if not value:
        return None

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            pass

    try:
        date = datetime.datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        msg = "Invalid {}: {} (expected YYYY-MM-DD[ HH:MM[:SS]])".format(option, value)
        raise utils.D2DockerError(msg)

    return date + datetime.timedelta(days=1) if end_of_day else date


def print_table(entries):
    rows = [
        [entry.time.strftime("%Y-%m-%d %H:%M:%S"), entry.status, entry.method, entry.user or "-", entry.url]
        for entry in entries
    ]
    if not rows:
        return

    # Pad every column but the last one (url) to its widest value
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]) - 1)]
    for row in rows:
        padded = [value.ljust(width) for value, width in zip(row, widths)]
        print("  ".join(padded + [row[-1]]))
