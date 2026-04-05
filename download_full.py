from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

from huggingface_hub import HfApi
from huggingface_hub.errors import BucketNotFoundError


DEFAULT_SOURCE = "https://huggingface.co/buckets/Ghisso/vscode_mounts/tree/RAG"
DEFAULT_DEST = Path("./.github")


def resolve_bucket_source(source: str) -> str:
    if source.startswith("hf://buckets/"):
        return source.rstrip("/")

    parsed = urlparse(source)
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in {"huggingface.co", "www.huggingface.co"}:
        raise ValueError("Expected a Hugging Face bucket URL or an hf://buckets/... path.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "buckets":
        raise ValueError(
            "Expected a bucket URL like https://huggingface.co/buckets/<namespace>/<bucket>/tree/<prefix>."
        )

    bucket_id = f"{parts[1]}/{parts[2]}"
    prefix_parts = parts[4:] if len(parts) > 3 and parts[3] == "tree" else parts[3:]

    source_path = f"hf://buckets/{bucket_id}"
    if prefix_parts:
        source_path = f"{source_path}/{'/'.join(prefix_parts)}"
    return source_path


def resolve_token() -> str | bool:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync a Hugging Face bucket path into a local directory."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Bucket web URL or hf://buckets/... path to sync from.",
    )
    parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help="Local directory that should receive the bucket contents.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sync plan as JSONL without downloading files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = resolve_bucket_source(args.source)
    destination = Path(args.dest)

    print(f"Source: {source}")
    print(f"Destination: {destination.resolve()}")

    api = HfApi()
    try:
        plan = api.sync_bucket(
            source=source,
            dest=str(destination),
            dry_run=args.dry_run,
            token=resolve_token(),
        )
    except BucketNotFoundError as error:
        raise SystemExit(
            "Bucket not found or access denied. If it is private, run hf auth login or export HF_TOKEN."
        ) from error
    except OSError as error:
        raise SystemExit(f"Sync failed: {error}") from error

    summary = plan.summary()
    print(
        "Summary: "
        f"{summary['downloads']} downloads, "
        f"{summary['skips']} skips, "
        f"{summary['deletes']} deletes, "
        f"{summary['total_size']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())