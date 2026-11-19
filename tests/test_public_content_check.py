"""Exercise the publication gate against isolated Git object databases."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools/public_content_check.py"
HOOK = ROOT / ".githooks/pre-push"
PRIVATE_IP = "192.168." + "44.9"
PRIVATE_PATH = "/" + "Users" + "/a-user/notes.txt"
SAMPLE_TOKEN = "gh" + "p_" + "z" * 36


def git(path, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=check,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    )


def checker(path, *args, data=None):
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        input=data,
        capture_output=True,
        text=True,
        cwd=path,
        check=False,
    )


def write(path, name, content):
    file = path / name
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_text(content, encoding="utf-8")


def commit(path, message="Example change"):
    git(path, "add", "-A")
    git(path, "commit", "-m", message)
    return git(path, "rev-parse", "HEAD").stdout.strip()


def new_ref(oid, ref="refs/heads/topic"):
    return f"{ref} {oid} {ref} {'0' * len(oid)}\n"


@pytest.fixture
def repositories(tmp_path):
    source = tmp_path / "working"
    target = tmp_path / "published"
    git(tmp_path, "init", "-b", "main", str(source))
    git(tmp_path, "init", "--bare", str(target))
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@example.com")
    write(source, "README.md", "# Reference\n\nReviewed protocol word: 001F.\n")
    base = commit(source, "Base")
    git(source, "remote", "add", "publication", str(target))
    git(source, "push", "publication", "main")
    return source, target, base


def test_staged_content_cannot_be_hidden_by_a_worktree_edit(repositories):
    source, _, _ = repositories
    write(source, "docs/note.md", PRIVATE_PATH + "\n" + PRIVATE_IP)
    git(source, "add", "docs/note.md")
    write(source, "docs/note.md", "Reviewed content.")

    result = checker(source, "--staged")

    assert result.returncode == 1
    assert "docs/note.md" in result.stderr
    assert "local absolute path" in result.stderr
    assert "private IPv4 address" in result.stderr
    assert PRIVATE_PATH not in result.stderr
    assert PRIVATE_IP not in result.stderr


def test_renamed_diagnostics_and_fixture_contents_are_checked(repositories):
    source, _, _ = repositories
    write(
        source, "saved-notes.txt", '{"data":{"chunks":[{"elapsed_ms":1,"hex":"bc"}]}}'
    )
    write(source, "tests/fixtures/changed.json", '{"note":"' + SAMPLE_TOKEN + '"}')
    write(source, "proxon-research-archive/notes.md", "A private timeline")
    git(source, "add", "-A")

    result = checker(source, "--staged")

    assert result.returncode == 1
    assert "'saved-notes.txt': recording or diagnostic export" in result.stderr
    assert "'tests/fixtures/changed.json': credential pattern" in result.stderr
    assert (
        "'proxon-research-archive/notes.md': private working directory" in result.stderr
    )
    assert SAMPLE_TOKEN not in result.stderr


def test_unpublished_commit_with_leak_is_checked_even_when_tip_is_clean(repositories):
    source, target, base = repositories
    write(source, "accidental.md", PRIVATE_IP)
    commit(source)
    (source / "accidental.md").unlink()
    tip = commit(source)

    for result in (
        checker(source, "--base", base, "--head", tip),
        checker(source, "--pre-push", str(target), data=new_ref(tip)),
    ):
        assert result.returncode == 1
        assert "'accidental.md': private IPv4 address" in result.stderr


def test_published_baseline_is_specific_to_actual_destination(repositories, tmp_path):
    source, target, _ = repositories
    write(source, "old.md", "Published fixture host: " + PRIVATE_IP + "\n")
    commit(source)
    git(source, "push", "publication", "main")
    write(source, "old.md", "Unchanged earlier fixture host: " + PRIVATE_IP + "\n")
    tip = commit(source)

    known = checker(source, "--pre-push", str(target), data=new_ref(tip))
    assert known.returncode == 0, known.stderr

    other = tmp_path / "another-publication"
    git(tmp_path, "init", "--bare", str(other))
    unknown = checker(source, "--pre-push", str(other), data=new_ref(tip))
    assert unknown.returncode == 1
    assert "'old.md': private IPv4 address" in unknown.stderr


def test_multiple_updates_include_commit_and_annotated_tag_messages(repositories):
    source, target, base = repositories
    tip = commit_empty(source, "Private location " + PRIVATE_PATH)
    git(
        source,
        "tag",
        "-a",
        "fixture-tag",
        "-m",
        "Unpublished credential " + SAMPLE_TOKEN,
    )
    tag = git(source, "rev-parse", "fixture-tag").stdout.strip()
    updates = (
        f"refs/heads/main {tip} refs/heads/main {base}\n"
        + new_ref(tag, "refs/tags/fixture-tag")
        + f"(delete) {'0' * len(base)} refs/heads/old {base}\n"
    )

    result = checker(source, "--pre-push", str(target), data=updates)

    assert result.returncode == 1
    assert f"'commit {tip[:12]}': local absolute path" in result.stderr
    assert f"'tag {tag[:12]}': credential pattern" in result.stderr
    assert SAMPLE_TOKEN not in result.stderr


def commit_empty(path, message):
    git(path, "commit", "--allow-empty", "-m", message)
    return git(path, "rev-parse", "HEAD").stdout.strip()


def test_merge_resolution_can_introduce_private_content(repositories):
    source, _, base = repositories
    git(source, "switch", "-c", "topic")
    write(source, "README.md", "# Proposed setup\n")
    commit(source)
    git(source, "switch", "main")
    write(source, "README.md", "# Released setup\n")
    main = commit(source)
    assert git(source, "merge", "topic", check=False).returncode != 0
    write(source, "README.md", "# Merged setup\n" + PRIVATE_IP)
    tip = commit(source)

    result = checker(source, "--base", base, "--head", tip)

    assert result.returncode == 1 and "'README.md'" in result.stderr
    assert checker(source, "--base", base, "--head", main).returncode == 0


def test_common_hook_is_enforced_from_linked_worktree(repositories, tmp_path):
    source, target, _ = repositories
    hooks = source / ".git/hooks"
    shutil.copy2(HOOK, hooks / "pre-push")
    shutil.copy2(CHECKER, hooks / CHECKER.name)
    git(source, "config", "core.hooksPath", str(hooks))
    linked = tmp_path / "linked-worktree"
    git(source, "worktree", "add", "-b", "topic", str(linked))
    write(linked, "internal.md", PRIVATE_IP)
    commit(linked)

    push = git(linked, "push", "publication", "topic", check=False)

    assert push.returncode != 0
    assert "'internal.md': private IPv4 address" in push.stderr
    assert git(
        target, "show-ref", "--verify", "refs/heads/topic", check=False
    ).returncode


def test_failure_to_inspect_destination_blocks_push(repositories, tmp_path):
    source, _, base = repositories

    result = checker(
        source, "--pre-push", str(tmp_path / "not-a-repo"), data=new_ref(base)
    )

    assert result.returncode == 2
    assert "git ls-remote failed" in result.stderr


def test_release_words_and_reviewed_protocol_vectors_still_pass(repositories):
    source, _, base = repositories
    write(source, "docs/REFERENCE.md", "Version 0.16.10. Compare HESP sender 118000.")
    target = source / "custom_components/proxon_hesp/brand/logo.png"
    target.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "custom_components/proxon_hesp/brand/logo.png", target)
    write(source, "tests/fixtures/synthetic.json", '[{"t_ms":125,"frame":"10ae00"}]')
    tip = commit(source)

    result = checker(source, "--base", base, "--head", tip)

    assert result.returncode == 0, result.stderr

    target.write_bytes(target.read_bytes() + b"replacement")
    git(source, "add", "-A")
    result = checker(source, "--staged")
    assert result.returncode == 1
    assert "unreviewed brand image" in result.stderr
