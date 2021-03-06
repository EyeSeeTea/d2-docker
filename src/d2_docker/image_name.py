import collections

Parts = collections.namedtuple("Parts", ["organisation", "type", "version", "name"])


class ImageName:
    def __init__(self, parts):
        self.parts = parts

    def get(self):
        p = self.parts
        string_parts = [
            p.organisation,
            "/",
            p.type,
            ":",
            "-".join(filter(bool, [p.version, p.name])),
        ]
        return "".join(string_parts)

    def with_version(self, new_version):
        new_parts = self.parts._replace(version=new_version)
        return ImageName(new_parts)

    def with_type(self, new_type):
        new_parts = self.parts._replace(type=new_type)
        return ImageName(new_parts)

    def with_name(self, new_name):
        new_parts = self.parts._replace(name=new_name)
        return ImageName(new_parts)

    def core(self):
        return self.with_type("dhis2-core").with_name("")

    @property
    def version(self):
        return self.parts.version

    @staticmethod
    def from_string(s):
        organisation, rest1 = split(s, "/", 2)
        type_, rest2 = split(rest1, ":", 2)
        version, name = split(rest2, "-", 2, min_length=1)
        parts = Parts(organisation=organisation, type=type_, version=version, name=name)
        return ImageName(parts)


def split(s, splitchar, max_length, min_length=None):
    min_length_ = max_length if min_length is None else min_length
    sp = s.split(splitchar, max_length - 1)
    if len(sp) < min_length_:
        raise ValueError(
            "Cannot split {} (splitchar={}, expected_length={})".format(s, splitchar, max_length)
        )
    else:
        return [None] * (max_length - len(sp)) + sp


def iter_versions(start, end):
    start_major, start_minor = split(start, ".", 2)
    end_major, end_minor = split(end, ".", 2)
    if start_major != end_major:
        raise ValueError("Only same major versions supported")
    else:
        return [
            "{}.{}".format(start_major, minor_version)
            for minor_version in range(int(start_minor), int(end_minor) + 1)
        ]
