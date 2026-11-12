"""Write release notes for stable v2.x tags newer than a given tag: notes_since.py <out.md> <after-tag> <release.json>..."""
import json, re, sys

out_path, after = sys.argv[1], sys.argv[2]
rels = [r for path in sys.argv[3:] for r in json.load(open(path))]
rels.sort(key=lambda r: r["published_at"])
after_time = next(r["published_at"] for r in rels if r["tag_name"] == after)
with open(out_path, "w") as out:
    for r in rels:
        if r["published_at"] > after_time and not r["prerelease"]:
            out.write(f"\n\n######## {r['tag_name']} published {r['published_at']} prerelease={r['prerelease']}\n")
            out.write((r.get("body") or "").replace("\r\n", "\n"))
            print(r["tag_name"], r["published_at"], len(r.get("body") or ""))
