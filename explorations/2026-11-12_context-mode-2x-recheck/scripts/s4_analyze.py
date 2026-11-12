"""S4: summarize an strace file: network syscalls, and every path the process tried to create/write/remove.
Usage: python3 -I s4_analyze.py <run-dir> <strace.txt>
Paths under <run-dir> are shown relative; anything else is flagged OUTSIDE.
"""
import collections
import re
import sys

run, trace = sys.argv[1].rstrip("/"), sys.argv[2]
net = collections.Counter()
writes = collections.OrderedDict()
WRITE_FLAGS = re.compile(r"O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|O_APPEND")
for line in open(trace, errors="replace"):
    m = re.match(r"\d+\s+(\w+)\((.*)", line)
    if not m:
        continue
    call, rest = m.groups()
    result = rest.rsplit("=", 1)[-1].strip()
    if call in ("socket", "connect", "sendto", "sendmsg", "bind", "listen", "accept", "accept4", "recvfrom"):
        net[(call, re.sub(r"\s+", " ", rest.split(")")[0])[:110], result.split()[0] if result else "?")] += 1
    paths = []
    if call in ("openat", "open"):
        if WRITE_FLAGS.search(rest):
            paths = re.findall(r'"([^"]*)"', rest)[:1]
    elif call in ("symlink", "symlinkat"):
        paths = re.findall(r'"([^"]*)"', rest)[-1:]  # the link location, not its target
    elif call in ("mkdir", "mkdirat", "unlink", "unlinkat", "rmdir", "rename", "renameat", "renameat2", "link", "linkat", "chmod", "fchmodat", "truncate", "utimensat", "chown", "fchownat"):
        paths = re.findall(r'"([^"]*)"', rest)[:2]
    for p in paths:
        key = (call, p)
        writes.setdefault(key, result.split()[0] if result else "?")
print("== network syscalls (call, args, result): count")
for (call, args, res), n in sorted(net.items()):
    print(f"  {call:9s} {args:110s} -> {res}  x{n}")
print("== write/create/remove attempts, grouped")
outside = []
for (call, p), res in writes.items():
    if p.startswith(run + "/"):
        continue
    outside.append((call, p, res))
inside = [(c, p[len(run) + 1:], r) for (c, p), r in writes.items() if p.startswith(run + "/")]
areas = collections.Counter(p.split("/")[0] + ("/" + p.split("/")[1] if p.startswith(("repo/", "home/", "tmp/")) and len(p.split("/")) > 1 else "") for _, p, _ in inside)
for area, n in sorted(areas.items()):
    print(f"  inside run folder: {area}: {n} path operations")
print("== operations OUTSIDE the run folder (call, path, result):")
for c, p, r in outside:
    print(f"  {c:10s} {p}  -> {r}")
if not outside:
    print("  (none)")
print("== inside-run operations not under the data root (call, path, result):")
for c, p, r in inside:
    if not p.startswith("repo/.claude/.cache/context-mode"):
        print(f"  {c:10s} {p}  -> {r}")
