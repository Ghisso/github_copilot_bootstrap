"""Replace selected .github directories from a Hugging Face bucket."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from huggingface_hub import BucketFile, HfApi
from huggingface_hub.errors import BucketNotFoundError



BUCKET_PREFIX = "hf://buckets/"
DEFAULT_SOURCE = "https://huggingface.co/buckets/Ghisso/vscode_mounts/tree/RAG"
DEFAULT_DEST = Path("./.github")
TARGET_DIRECTORIES = ("agents", "skills", "hooks", "instructions")
PRESERVED_AGENT_PATH = Path("agents/domain-reviewer.agent.md")


def resolve_bucket_source(source: str) -> str:
	"""Normalize a bucket URL to the hf://buckets/... form.

	Args:
		source: Bucket web URL or hf://buckets/... path.

	Returns:
		Normalized bucket source path.

	Raises:
		ValueError: If the source does not point to a Hugging Face bucket.
	"""
	if source.startswith(BUCKET_PREFIX):
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
	source_path = f"{BUCKET_PREFIX}{bucket_id}"
	if prefix_parts:
		source_path = f"{source_path}/{'/'.join(prefix_parts)}"
	return source_path


def split_bucket_source(source: str) -> tuple[str, str]:
	"""Split a normalized bucket source into bucket id and prefix.

	Args:
		source: Bucket web URL or hf://buckets/... path.

	Returns:
		Tuple of bucket id and prefix inside the bucket.

	Raises:
		ValueError: If the source does not contain a valid bucket id.
	"""
	normalized_source = resolve_bucket_source(source)
	relative_source = normalized_source.removeprefix(BUCKET_PREFIX)
	parts = [part for part in relative_source.split("/") if part]
	if len(parts) < 2:
		raise ValueError("Expected a bucket id in the form <namespace>/<bucket>.")

	bucket_id = f"{parts[0]}/{parts[1]}"
	prefix = "/".join(parts[2:])
	return bucket_id, prefix


def resolve_remote_prefix(base_prefix: str, directory_name: str) -> str:
	"""Build the remote prefix for a target directory.

	Args:
		base_prefix: Root prefix inside the bucket.
		directory_name: Directory to replace locally.

	Returns:
		Remote prefix for the directory.
	"""
	return f"{base_prefix}/{directory_name}" if base_prefix else directory_name


def resolve_token() -> str | bool:
	"""Resolve the Hugging Face token to use for bucket access.

	Returns:
		Configured token string, or True to use the local HF auth state.
	"""
	return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or True


def parse_args() -> argparse.Namespace:
	"""Parse command line arguments.

	Returns:
		Parsed script arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Replace selected .github directories from a Hugging Face bucket."
	)
	parser.add_argument(
		"--source",
		default=DEFAULT_SOURCE,
		help="Bucket web URL or hf://buckets/... path to sync from.",
	)
	parser.add_argument(
		"--dest",
		default=str(DEFAULT_DEST),
		help="Local .github directory to update.",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Show what would be replaced without modifying local files.",
	)
	parser.add_argument(
		"--full",
		action="store_true",
		help="Sync the entire bucket path as-is using HF sync_bucket instead of selective directory replacement.",
	)
	return parser.parse_args()


def list_remote_files(api: HfApi, bucket_id: str, remote_prefix: str, token: str | bool) -> list[BucketFile]:
	"""List all remote files for a directory prefix.

	Args:
		api: Hugging Face API client.
		bucket_id: Bucket id in the form <namespace>/<bucket>.
		remote_prefix: Prefix to list under the bucket.
		token: Token or auth sentinel for bucket access.

	Returns:
		Remote files available under the requested prefix.

	Raises:
		ValueError: If the remote prefix does not contain any files.
	"""
	remote_files = [
		item
		for item in api.list_bucket_tree(bucket_id, prefix=remote_prefix, recursive=True, token=token)
		if isinstance(item, BucketFile)
	]
	if not remote_files:
		raise ValueError(f"No files found for '{remote_prefix}' in bucket '{bucket_id}'.")
	return remote_files


def collect_remote_targets(api: HfApi, bucket_id: str, base_prefix: str, token: str | bool) -> dict[str, tuple[str, list[BucketFile]]]:
	"""Collect remote files for all targeted local directories.

	Args:
		api: Hugging Face API client.
		bucket_id: Bucket id in the form <namespace>/<bucket>.
		base_prefix: Root prefix inside the bucket.
		token: Token or auth sentinel for bucket access.

	Returns:
		Mapping of directory name to its remote prefix and files.
	"""
	remote_targets: dict[str, tuple[str, list[BucketFile]]] = {}
	for directory_name in TARGET_DIRECTORIES:
		remote_prefix = resolve_remote_prefix(base_prefix, directory_name)
		remote_targets[directory_name] = (remote_prefix, list_remote_files(api, bucket_id, remote_prefix, token))
	return remote_targets


def count_local_files(directory: Path) -> int:
	"""Count files currently present in a local directory tree.

	Args:
		directory: Directory to inspect.

	Returns:
		Number of files inside the directory tree.

	Raises:
		ValueError: If the path exists but is not a directory.
	"""
	if not directory.exists():
		return 0
	if not directory.is_dir():
		raise ValueError(f"Expected directory at '{directory}', found a non-directory path.")
	return sum(1 for path in directory.rglob("*") if path.is_file())


def backup_preserved_agent(destination: Path, temp_dir: Path) -> Path:
	"""Backup the domain reviewer file that must survive replacement.

	Args:
		destination: Local .github directory.
		temp_dir: Temporary directory to hold the backup.

	Returns:
		Path to the temporary backup file.

	Raises:
		ValueError: If the preserved local file does not exist.
	"""
	preserved_file = destination / PRESERVED_AGENT_PATH
	if not preserved_file.is_file():
		raise ValueError(f"Preserved file '{preserved_file}' does not exist.")

	backup_path = temp_dir / preserved_file.name
	shutil.copy2(preserved_file, backup_path)
	return backup_path


def relative_remote_path(remote_path: str, remote_prefix: str) -> PurePosixPath:
	"""Convert a remote bucket path into a path relative to its directory prefix.

	Args:
		remote_path: Full remote path inside the bucket.
		remote_prefix: Prefix used to list the directory.

	Returns:
		Relative path beneath the directory prefix.

	Raises:
		ValueError: If the remote path is not under the expected prefix.
	"""
	try:
		return PurePosixPath(remote_path).relative_to(PurePosixPath(remote_prefix))
	except ValueError as error:
		raise ValueError(f"Remote path '{remote_path}' is not under prefix '{remote_prefix}'.") from error


def replace_local_directory(
	api: HfApi,
	bucket_id: str,
	destination: Path,
	directory_name: str,
	remote_prefix: str,
	remote_files: list[BucketFile],
	token: str | bool,
	dry_run: bool,
	preserved_backup: Path | None,
) -> tuple[int, int]:
	"""Replace one local directory with the corresponding bucket directory.

	Args:
		api: Hugging Face API client.
		bucket_id: Bucket id in the form <namespace>/<bucket>.
		destination: Local .github directory.
		directory_name: Directory to replace locally.
		remote_prefix: Prefix for the remote directory.
		remote_files: Remote files already collected for this directory.
		token: Token or auth sentinel for bucket access.
		dry_run: Whether to avoid local modifications.
		preserved_backup: Backup file for the preserved agent, when applicable.

	Returns:
		Tuple of local file count and remote file count.

	Raises:
		ValueError: If the target path exists and is not a directory.
	"""
	target_dir = destination / directory_name
	local_file_count = count_local_files(target_dir)
	remote_file_count = len(remote_files)
	preserve_note = " (preserving domain-reviewer.agent.md)" if directory_name == "agents" else ""
	print(
		f"{'Would replace' if dry_run else 'Replacing'} {target_dir} "
		f"with {remote_file_count} remote files{preserve_note}."
	)

	if dry_run:
		return local_file_count, remote_file_count

	if target_dir.exists() and not target_dir.is_dir():
		raise ValueError(f"Expected directory at '{target_dir}', found a non-directory path.")

	if target_dir.exists():
		shutil.rmtree(target_dir)
	target_dir.mkdir(parents=True, exist_ok=True)

	download_targets: list[tuple[str | BucketFile, str | Path]] = []
	for remote_file in remote_files:
		relative_path = relative_remote_path(remote_file.path, remote_prefix)
		local_path = target_dir / Path(*relative_path.parts)
		download_targets.append((remote_file, local_path))

	api.download_bucket_files(bucket_id=bucket_id, files=download_targets, token=token)

	if directory_name == "agents" and preserved_backup is not None:
		restored_file = destination / PRESERVED_AGENT_PATH
		restored_file.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(preserved_backup, restored_file)

	return local_file_count, remote_file_count


def main() -> int:
	"""Replace selected .github directories from the configured bucket.

	Returns:
		Process exit code.
	"""
	args = parse_args()
	destination = Path(args.dest)
	token = resolve_token()

	if args.full:
		source = resolve_bucket_source(args.source)
		print(f"Source: {source}")
		print(f"Destination: {destination.resolve()}")
		api = HfApi()
		try:
			plan = api.sync_bucket(source=source, dest=str(destination), dry_run=args.dry_run, token=token)
		except BucketNotFoundError as error:
			raise SystemExit(
				"Bucket not found or access denied. If it is private, run `hf auth login` or export HF_TOKEN."
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

	bucket_id, base_prefix = split_bucket_source(args.source)

	print(f"Source bucket: {bucket_id}")
	print(f"Source prefix: {base_prefix or '/'}")
	print(f"Destination root: {destination.resolve()}")

	api = HfApi()
	try:
		remote_targets = collect_remote_targets(api, bucket_id, base_prefix, token)
	except BucketNotFoundError as error:
		raise SystemExit(
			"Bucket not found or access denied. If it is private, run `hf auth login` or export HF_TOKEN."
		) from error
	except OSError as error:
		raise SystemExit(f"Failed to inspect the bucket: {error}") from error
	except ValueError as error:
		raise SystemExit(str(error)) from error

	total_local_files = 0
	total_remote_files = 0
	for directory_name in TARGET_DIRECTORIES:
		remote_prefix, remote_files = remote_targets[directory_name]
		local_file_count, remote_file_count = replace_local_directory(
			api=api,
			bucket_id=bucket_id,
			destination=destination,
			directory_name=directory_name,
			remote_prefix=remote_prefix,
			remote_files=remote_files,
			token=token,
			dry_run=True,
			preserved_backup=None,
		)
		total_local_files += local_file_count
		total_remote_files += remote_file_count

	if args.dry_run:
		print(
			"Summary: "
			f"would replace {len(TARGET_DIRECTORIES)} directories, "
			f"remove {total_local_files} local files, "
			f"download {total_remote_files} remote files."
		)
		return 0

	if destination.exists() and not destination.is_dir():
		raise SystemExit(f"Expected destination directory at '{destination}'.")
	destination.mkdir(parents=True, exist_ok=True)

	try:
		with tempfile.TemporaryDirectory() as temp_dir_name:
			preserved_backup = backup_preserved_agent(destination, Path(temp_dir_name))
			for directory_name in TARGET_DIRECTORIES:
				remote_prefix, remote_files = remote_targets[directory_name]
				replace_local_directory(
					api=api,
					bucket_id=bucket_id,
					destination=destination,
					directory_name=directory_name,
					remote_prefix=remote_prefix,
					remote_files=remote_files,
					token=token,
					dry_run=False,
					preserved_backup=preserved_backup,
				)
	except BucketNotFoundError as error:
		raise SystemExit(
			"Bucket not found or access denied. If it is private, run `hf auth login` or export HF_TOKEN."
		) from error
	except OSError as error:
		raise SystemExit(f"Replacement failed: {error}") from error
	except ValueError as error:
		raise SystemExit(str(error)) from error

	print(
		"Summary: "
		f"replaced {len(TARGET_DIRECTORIES)} directories, "
		f"removed {total_local_files} local files, "
		f"downloaded {total_remote_files} remote files."
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())