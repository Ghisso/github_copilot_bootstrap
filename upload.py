"""Upload selected .github directories to a Hugging Face bucket."""

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub.errors import BucketNotFoundError

from download import (
    BUCKET_PREFIX,
    DEFAULT_SOURCE,
    PRESERVED_AGENT_PATH,
    TARGET_DIRECTORIES,
    count_local_files,
    resolve_remote_prefix,
    resolve_token,
    split_bucket_source,
)


DEFAULT_ROOT = Path("./.github")
SUMMARY_KEYS = ("uploads", "downloads", "deletes", "skips", "total_size")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Optional command line arguments.

    Returns:
        Parsed script arguments.
    """
    parser = argparse.ArgumentParser(
        description="Sync selected local .github directories to a Hugging Face bucket."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Bucket web URL or hf://buckets/... path to sync to.",
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Local .github directory to upload from.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply remote changes. Without this flag the script only previews the sync.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed per-file sync output from huggingface_hub.",
    )
    return parser.parse_args(argv)


def resolve_local_directory(root: Path, directory_name: str) -> Path:
    """Resolve a local target directory and validate that it is safe to sync.

    Args:
        root: Local .github root directory.
        directory_name: Directory name that should be uploaded.

    Returns:
        Validated local directory path.

    Raises:
        ValueError: If the target directory is missing, is not a directory, or is empty.
    """
    directory = root / directory_name
    if not directory.exists():
        raise ValueError(f"Expected local directory at '{directory}', but it does not exist.")
    if not directory.is_dir():
        raise ValueError(f"Expected local directory at '{directory}', found a non-directory path.")

    local_file_count = count_local_files(directory)
    if local_file_count == 0:
        raise ValueError(f"Refusing to sync empty directory '{directory}'.")
    return directory


def build_remote_destination(bucket_id: str, base_prefix: str, directory_name: str) -> str:
    """Build the bucket destination for one target directory.

    Args:
        bucket_id: Bucket id in the form <namespace>/<bucket>.
        base_prefix: Root prefix inside the bucket.
        directory_name: Directory name that should be uploaded.

    Returns:
        Remote destination in hf://buckets/... form.
    """
    remote_prefix = resolve_remote_prefix(base_prefix, directory_name)
    return f"{BUCKET_PREFIX}{bucket_id}/{remote_prefix}" if remote_prefix else f"{BUCKET_PREFIX}{bucket_id}"


def preserved_exclude_patterns(directory_name: str) -> list[str]:
    """Return remote preserve exclusions for a target directory.

    Args:
        directory_name: Directory name that should be uploaded.

    Returns:
        Exclude patterns that must be ignored during sync.
    """
    preserved_parts = PRESERVED_AGENT_PATH.parts
    if not preserved_parts or directory_name != preserved_parts[0]:
        return []
    return [Path(*preserved_parts[1:]).as_posix()]


def format_summary(directory_name: str, summary: Mapping[str, int]) -> str:
    """Format a sync summary for console output.

    Args:
        directory_name: Directory that was synced.
        summary: Sync summary returned by huggingface_hub.

    Returns:
        Formatted summary line.
    """
    return (
        f"Summary ({directory_name}): "
        f"{summary.get('uploads', 0)} uploads, "
        f"{summary.get('downloads', 0)} downloads, "
        f"{summary.get('deletes', 0)} deletes, "
        f"{summary.get('skips', 0)} skips, "
        f"{summary.get('total_size', 0)} bytes"
    )


def merge_summaries(total: dict[str, int], current: Mapping[str, int]) -> None:
    """Accumulate per-directory sync summaries.

    Args:
        total: Mutable total summary.
        current: Current directory summary.
    """
    for key in SUMMARY_KEYS:
        total[key] += int(current.get(key, 0))


def sync_target_directory(
    api: HfApi,
    bucket_id: str,
    base_prefix: str,
    root: Path,
    directory_name: str,
    token: str | bool,
    execute: bool,
    verbose: bool,
) -> dict[str, int]:
    """Preview or execute a sync for one target directory.

    Args:
        api: Hugging Face API client.
        bucket_id: Bucket id in the form <namespace>/<bucket>.
        base_prefix: Root prefix inside the bucket.
        root: Local .github root directory.
        directory_name: Directory name that should be uploaded.
        token: Token or auth sentinel for bucket access.
        execute: Whether to apply remote changes.
        verbose: Whether to let huggingface_hub print detailed output.

    Returns:
        Sync summary returned by huggingface_hub.
    """
    local_directory = resolve_local_directory(root, directory_name)
    local_file_count = count_local_files(local_directory)
    remote_destination = build_remote_destination(bucket_id, base_prefix, directory_name)
    exclude_patterns = preserved_exclude_patterns(directory_name) or None

    preserve_note = ""
    if exclude_patterns:
        preserve_note = f" (preserving remote {PRESERVED_AGENT_PATH.as_posix()})"

    action = "Syncing" if execute else "Previewing"
    print(
        f"{action} {local_directory} -> {remote_destination} with {local_file_count} local files{preserve_note}."
    )

    plan = api.sync_bucket(
        source=str(local_directory),
        dest=remote_destination,
        delete=True,
        dry_run=not execute,
        exclude=exclude_patterns,
        verbose=verbose,
        quiet=not verbose,
        token=token,
    )
    raw_summary = plan.summary()
    summary = {key: int(raw_summary.get(key, 0)) for key in SUMMARY_KEYS}
    print(format_summary(directory_name, summary))
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """Upload selected local .github directories to the configured bucket.

    Args:
        argv: Optional command line arguments.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    bucket_id, base_prefix = split_bucket_source(args.source)
    root = Path(args.root)
    token = resolve_token()

    if not root.exists():
        raise SystemExit(f"Expected local root directory at '{root}'.")
    if not root.is_dir():
        raise SystemExit(f"Expected local root directory at '{root}', found a non-directory path.")

    print(f"Source bucket: {bucket_id}")
    print(f"Source prefix: {base_prefix or '/'}")
    print(f"Local source root: {root.resolve()}")
    print(f"Mode: {'execute' if args.execute else 'preview'}")
    if not args.execute:
        print("Preview mode only. Re-run with --execute to apply remote changes.")

    api = HfApi()
    total_summary = {key: 0 for key in SUMMARY_KEYS}
    try:
        for directory_name in TARGET_DIRECTORIES:
            summary = sync_target_directory(
                api=api,
                bucket_id=bucket_id,
                base_prefix=base_prefix,
                root=root,
                directory_name=directory_name,
                token=token,
                execute=args.execute,
                verbose=args.verbose,
            )
            merge_summaries(total_summary, summary)
    except BucketNotFoundError as error:
        raise SystemExit(
            "Bucket not found or access denied. If it is private, run `hf auth login` or export HF_TOKEN."
        ) from error
    except OSError as error:
        raise SystemExit(f"Upload failed: {error}") from error
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print(
        "Total summary: "
        f"{total_summary['uploads']} uploads, "
        f"{total_summary['downloads']} downloads, "
        f"{total_summary['deletes']} deletes, "
        f"{total_summary['skips']} skips, "
        f"{total_summary['total_size']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())