"""Write calls-s3.json: the ordered ctx_index / ctx_search calls for S3."""
import json, pathlib
HERE = pathlib.Path(__file__).resolve().parent.parent
def idx(p):
    return {"method": "tools/call", "params": {"name": "ctx_index", "arguments": {"path": p}}, "_timeout": 300}
def srch(q):
    return {"method": "tools/call", "params": {"name": "ctx_search", "arguments": {"queries": [q]}}}
calls = [
    idx("bulk"),
    srch("zzzznomatchzzzz"),            # no match: reply states how many sources are indexed
    srch("ignoredtoken"), srch("ignoreddirtoken"),
    srch("siblingtoken"), srch("siblingdirtoken"), srch("outsidetoken"),
    srch("bulktoken000"), srch("bulktoken007"), srch("bulktoken299"),
    idx("deep"), srch("deeptoken"),
    idx("many"), srch("zzzznomatchzzzz"), srch("manytoken2999"),
    idx("huge/big.txt"), srch("hugetoken0399999"),
    idx("../sibling.txt"),               # outside the repo, inside the repo's parent folder
    idx(str(HERE / "outside-parent.txt")),  # outside the parent
    idx("bulk/link-sibling.txt"),        # a symlink given as the path itself
    idx("bulk/link-outside.txt"),
]
(HERE / "scripts/calls-s3.json").write_text(json.dumps(calls, indent=1))
print(len(calls), "calls")
