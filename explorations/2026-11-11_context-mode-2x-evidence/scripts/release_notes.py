import json
import sys

releases = json.load(open(sys.argv[1]))
with open(sys.argv[2], "w") as out:
    for rel in reversed(releases):
        tag = rel["tag_name"]
        if tag.startswith("v2.") or tag == "v1.0.169":
            header = "\n\n######## %s  published %s  prerelease=%s\n" % (
                tag, rel["published_at"], rel["prerelease"])
            out.write(header)
            out.write((rel.get("body") or "").replace("\r\n", "\n"))
