"""S3: build the folder-index probe tree under run/s3 (git init only, no commit).

run/s3/                      <- parent of the repo (the server's containment root, per source)
  sibling.txt                outside the repo, inside the parent
  sibling-dir/inner.txt      same, a folder
  repo/                      Git repository
    .gitignore               ignored.txt, ignored-dir/
    bulk/                    300 small files, spread over depth 0..7 (d1/../d7)
      ignored.txt, ignored-dir/x.txt
      link-sibling.txt  -> run/s3/sibling.txt           (symlink to a file outside the repo, inside the parent)
      link-outside.txt  -> <scratch>/outside-parent.txt (symlink to a file outside the parent)
      link-dir          -> run/s3/sibling-dir           (symlink to a folder outside the repo)
    deep/                    1 file at depth 25
    many/                    3000 small files at depth 2
    huge/big.txt             one 20 MB file
<scratch>/outside-parent.txt outside everything
Usage: python3 -I s3_build.py
"""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
RUN = HERE / "run" / "s3"
REPO = RUN / "repo"
subprocess.run(["rm", "-rf", str(RUN)], check=True) if RUN.exists() else None
REPO.mkdir(parents=True)
subprocess.run(["git", "init", "-q", str(REPO)], check=True)
(REPO / "README.md").write_text("s3 fixture\n")
(REPO / ".gitignore").write_text("ignored.txt\nignored-dir/\n")
(RUN / "sibling.txt").write_text("siblingtoken only a sibling file\n")
(RUN / "sibling-dir").mkdir()
(RUN / "sibling-dir/inner.txt").write_text("siblingdirtoken inside a sibling folder\n")
(HERE / "outside-parent.txt").write_text("outsidetoken above the parent\n")

bulk = REPO / "bulk"
count = 0
for i in range(300):
    depth = i % 8  # 0..7 directories below bulk
    d = bulk.joinpath(*[f"d{n}" for n in range(1, depth + 1)])
    d.mkdir(parents=True, exist_ok=True)
    (d / f"f{i:03d}.txt").write_text(f"bulktoken{i:03d} depth{depth} small file number {i}\n")
    count += 1
(bulk / "ignored.txt").write_text("ignoredtoken must be skipped\n")
(bulk / "ignored-dir").mkdir()
(bulk / "ignored-dir/x.txt").write_text("ignoreddirtoken must be skipped\n")
(bulk / "link-sibling.txt").symlink_to(RUN / "sibling.txt")
(bulk / "link-outside.txt").symlink_to(HERE / "outside-parent.txt")
(bulk / "link-dir").symlink_to(RUN / "sibling-dir")

d = REPO / "deep"
for n in range(25):
    d = d / f"e{n}"
d.mkdir(parents=True)
(d / "bottom.txt").write_text("deeptoken at depth 25\n")

many = REPO / "many"
for i in range(3000):
    sub = many / f"g{i % 10}"
    sub.mkdir(parents=True, exist_ok=True)
    (sub / f"m{i:04d}.txt").write_text(f"manytoken{i:04d} small\n")

(REPO / "huge").mkdir()
(REPO / "huge/big.txt").write_text("".join(f"hugetoken{i:07d} filler line to make a big file\n" for i in range(400000)))
print("built", count, "bulk files + extras; huge bytes", (REPO / "huge/big.txt").stat().st_size)
