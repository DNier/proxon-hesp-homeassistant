"""Screen Git objects for private material before publishing them."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from functools import lru_cache
from pathlib import PurePosixPath

_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_GIT_ENV = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1"}
_DIFF = (
    "--raw",
    "-z",
    "--no-abbrev",
    "--no-renames",
    "--no-ext-diff",
    "--diff-filter=AMT",
)
_PRIVATE_DIRECTORIES = {
    "capture",
    "captures",
    "evidence",
    "private",
    "private-notes",
    "proxon-research-archive",
    "recordings",
    "tmp",
}
_PRIVATE_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".csv",
    ".db",
    ".flac",
    ".gif",
    ".gz",
    ".har",
    ".heic",
    ".jpeg",
    ".jpg",
    ".log",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".pcap",
    ".pcapng",
    ".pem",
    ".pfx",
    ".png",
    ".rar",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".tif",
    ".tiff",
    ".wav",
    ".webm",
    ".webp",
    ".zip",
}
_BRAND_IMAGES = {
    "custom_components/proxon_hesp/brand/icon.png",
    "custom_components/proxon_hesp/brand/logo.png",
}
_BRAND_SHA256 = "65dafad8ec2e3e11343677fc640c10f067c86191bc46bb477717cd0c19a15f0b"
_MAX_BLOB_SIZE = 8 * 1024 * 1024
_TEXT_PATTERNS = {
    "local absolute path": re.compile(
        r"(?<![\w/])/(?:Users|home|mnt|Volumes|private/(?:tmp|var)|var/folders|volume\d+)/"
        r"[^\s\x22\x27`\]\)]+|\b[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]"
        r"[^\s\x22\x27`\]\)]+"
    ),
    "private IPv4 address": re.compile(
        r"(?<![\w.])(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2[0-9]|3[01]))"
        r"(?:\.\d{1,3}){2}(?![\w.])"
    ),
    "private host": re.compile(
        r"(?i)(?<![\w.-])[a-z0-9][a-z0-9.-]*\.(?:synology\.me|local|lan|internal)"
        r"(?=[:/\x22\x27`\s>,\]\)]|$)"
    ),
    "credential pattern": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{25,}|"
        r"glpat-[A-Za-z0-9_-]{16,}|"
        r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{16,})\b|"
        r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b|"
        r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----|"
        r"(?i:https?://)[^\s/@:]+:[^\s/@]+@"
    ),
    "original media filename": re.compile(
        r"(?i)\b(?:IMG[_-]?\d+|DSC[_-]?\d+|VID[_-]?\d+)\.(?:jpe?g|heic|mov|mp4|png)\b"
    ),
}
_CAPTURE_KEYS = {"chunks", "started_utc", "received_utc", "elapsed_ms"}


class CheckError(Exception):
    """An outgoing object could not be checked."""


def git(*args, data=None, missing_ok=False):
    try:
        result = subprocess.run(
            ["git", *args], input=data, capture_output=True, env=_GIT_ENV, check=False
        )
    except OSError:
        raise CheckError("Git could not be started") from None
    if result.returncode:
        if missing_ok:
            return b""
        # Stderr can include URLs or other material that should not be printed.
        raise CheckError(f"git {args[0]} failed")
    return result.stdout


def _oid(value):
    if not _OBJECT_ID.fullmatch(value):
        raise CheckError("invalid Git object ID")
    return value


def _commit(ref):
    return _oid(
        git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
        .decode("ascii")
        .strip()
    )


def _text_findings(text):
    return Counter(
        (category, match.group())
        for category, pattern in _TEXT_PATTERNS.items()
        for match in pattern.finditer(text)
    )


def _path_category(path):
    parts = PurePosixPath(path.lower()).parts
    if set(parts[:-1]) & _PRIVATE_DIRECTORIES:
        return "private working directory"
    filename = parts[-1]
    if filename == ".env" or filename.startswith(".env."):
        return "local environment file"
    if (
        path not in _BRAND_IMAGES
        and PurePosixPath(filename).suffix in _PRIVATE_SUFFIXES
    ):
        return "media, archive, database or capture file"
    return None


def _capture_structure(value):
    remaining = [value]
    while remaining:
        item = remaining.pop()
        if isinstance(item, dict):
            if (
                (
                    ("capture" in item or "event_capture" in item)
                    and {"integration_version", "profile"}.issubset(item)
                )
                or ("chunks" in item and len(_CAPTURE_KEYS & item.keys()) > 1)
                or (
                    isinstance(item.get("chunks"), list)
                    and any(
                        isinstance(chunk, dict)
                        and "hex" in chunk
                        and ("received_utc" in chunk or "elapsed_ms" in chunk)
                        for chunk in item["chunks"]
                    )
                )
            ):
                return True
            remaining.extend(item.values())
        elif isinstance(item, list):
            remaining.extend(item)
    return False


@lru_cache(maxsize=512)
def _blob_findings(oid, inspect_json):
    raw = _blob_data(oid)
    if raw is None:
        return Counter({("file exceeds inspection size limit", ""): 1})
    try:
        if b"\0" in raw:
            return Counter({("binary file", ""): 1})
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return Counter({("binary file", ""): 1})
    findings = _text_findings(text)
    if inspect_json or text.lstrip().startswith(("{", "[")):
        try:
            if _capture_structure(json.loads(text)):
                findings[("recording or diagnostic export", "")] += 1
        except json.JSONDecodeError:
            if inspect_json and {"chunks", "hex"}.issubset(
                re.findall(r'"(\w+)"\s*:', text)
            ):
                findings[("recording or diagnostic export", "")] += 1
    return findings


def _blob_data(oid):
    if int(git("cat-file", "-s", oid)) > _MAX_BLOB_SIZE:
        return None
    return git("cat-file", "blob", oid)


def _diff_records(raw):
    if not raw:
        return {}
    if not raw.endswith(b"\0"):
        raise CheckError("invalid Git diff stream")
    parts = raw[:-1].split(b"\0")
    if len(parts) % 2:
        raise CheckError("invalid Git diff record")
    records = {}
    for index in range(0, len(parts), 2):
        meta, path = parts[index : index + 2]
        old_mode, new_mode, old_oid, new_oid, _ = meta.decode("ascii").split()
        name = os.fsdecode(path)
        records[name] = (old_mode[1:], new_mode, _oid(old_oid), _oid(new_oid))
    return records


def _is_zero(oid):
    return not oid.strip("0")


def _check_paths(diffs, findings):
    # A path present unchanged in any parent was checked when that parent was
    # first published. Include paths a merge introduced or changed on its own.
    common = set(diffs[0]).intersection(*(diff.keys() for diff in diffs[1:]))
    for path in common:
        _, mode, _, oid = diffs[0][path]
        if category := _path_category(path):
            findings.add((path, category))
            continue
        findings.update((path, category) for category, _ in _text_findings(path))
        if mode == "160000":
            findings.add((path, "unreviewed submodule"))
            continue
        if path in _BRAND_IMAGES:
            raw = _blob_data(oid)
            if (
                not raw
                or mode != "100644"
                or hashlib.sha256(raw).hexdigest() != _BRAND_SHA256
            ):
                findings.add((path, "unreviewed brand image"))
            continue
        inspect_json = path.lower().endswith((".json", ".jsonl"))
        baseline = Counter()
        for diff in diffs:
            old_mode, _, previous, _ = diff[path]
            if not _is_zero(previous) and old_mode != "160000":
                baseline |= _blob_findings(previous, inspect_json)
        current = _blob_findings(oid, inspect_json)
        findings.update(
            (path, category)
            for (category, match), count in current.items()
            if not match or count > baseline[(category, match)]
        )


def _check_message(raw, location, findings):
    _, _, message = raw.partition(b"\n\n")
    findings.update(
        (location, category)
        for category, _ in _text_findings(message.decode("utf-8", errors="replace"))
    )


def _history(heads, exclusions, findings):
    if not heads:
        return
    if git("rev-parse", "--is-shallow-repository").strip() == b"true":
        raise CheckError(
            "shallow history cannot be checked; fetch complete Git history"
        )
    ranges = [*sorted(heads), *(f"^{oid}" for oid in sorted(exclusions))]
    revisions = git("rev-list", "--stdin", data=("\n".join(ranges) + "\n").encode())
    for revision in revisions.decode("ascii").splitlines():
        oid = _oid(revision)
        raw = git("cat-file", "commit", oid)
        _check_message(raw, f"commit {oid[:12]}", findings)
        parents = [
            _oid(line[7:].decode("ascii"))
            for line in raw.split(b"\n\n", 1)[0].splitlines()
            if line.startswith(b"parent ")
        ]
        comparisons = (
            [
                git("diff-tree", "-r", "--no-commit-id", *_DIFF, parent, oid)
                for parent in parents
            ]
            if parents
            else [git("diff-tree", "--root", "-r", "--no-commit-id", *_DIFF, oid)]
        )
        _check_paths([_diff_records(diff) for diff in comparisons], findings)


def _push_targets(lines):
    heads, reported_remote = set(), set()
    for line in lines:
        fields = line.split()
        if len(fields) != 4:
            raise CheckError("invalid pre-push ref record")
        _, head, _, previous = fields
        if not _is_zero(_oid(previous)):
            reported_remote.add(previous)
        if not _is_zero(_oid(head)):
            heads.add(head)
    return heads, reported_remote


def _outgoing_tag(oid, published, findings):
    kind = git("cat-file", "-t", oid).strip()
    while kind == b"tag":
        raw = git("cat-file", "tag", oid)
        if oid not in published:
            _check_message(raw, f"tag {oid[:12]}", findings)
        object_line = raw.split(b"\n", 1)[0]
        if not object_line.startswith(b"object "):
            raise CheckError("invalid annotated Git tag")
        oid = _oid(object_line[7:].decode("ascii"))
        kind = git("cat-file", "-t", oid).strip()
    if kind != b"commit":
        raise CheckError(
            "push refers to a Git object other than a commit or commit tag"
        )
    return oid


def _check_push(destination, lines, findings):
    outgoing, published = _push_targets(lines)
    if not outgoing:
        return
    # Use the actual destination, not origin/main or a cached remote-tracking ref.
    advertised = git("ls-remote", "--refs", "--", destination)
    for line in advertised.splitlines():
        oid, _ = line.split(b"\t", 1)
        published.add(_oid(oid.decode("ascii")))
    exclusions = {
        _oid(peeled.decode("ascii").strip())
        for oid in published
        if (
            peeled := git("rev-parse", "--verify", f"{oid}^{{commit}}", missing_ok=True)
        )
    }
    heads = {_outgoing_tag(oid, published, findings) for oid in outgoing}
    _history(heads, exclusions, findings)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--base", help="Scan commits reachable from --head but not from BASE"
    )
    mode.add_argument(
        "--staged", action="store_true", help="Check the Git index against HEAD"
    )
    mode.add_argument("--pre-push", metavar="DESTINATION", help=argparse.SUPPRESS)
    parser.add_argument(
        "--head", default="HEAD", help="Outgoing commit for --base (default HEAD)"
    )
    args = parser.parse_args(argv)
    findings = set()
    try:
        if args.pre_push:
            _check_push(args.pre_push, sys.stdin, findings)
        elif args.staged:
            _check_paths([_diff_records(git("diff", "--cached", *_DIFF))], findings)
        else:
            _history({_commit(args.head)}, {_commit(args.base)}, findings)
    except (CheckError, ValueError, RecursionError) as err:
        print(
            "Public-content check could not complete: "
            + (
                str(err)
                if isinstance(err, CheckError)
                else "invalid Git object or export"
            ),
            file=sys.stderr,
        )
        return 2
    for path, category in sorted(findings):
        display = "<redacted path>" if _text_findings(path) else repr(path)
        print(f"Public-content check: {display}: {category}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
