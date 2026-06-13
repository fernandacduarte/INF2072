"""Tests for check_git_freshness.py."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import check_git_freshness as cgf


def _cp(args: list[str], rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args, returncode=rc, stdout=out, stderr=err)


def _install_git_stub(
    monkeypatch,
    responses: dict[tuple[str, tuple[str, ...]], object],
) -> None:
    def _fake_run(argv, capture_output, text, timeout, check):
        repo = str(Path(argv[2]).resolve())
        cmd = tuple(argv[3:])
        key = (repo, cmd)
        response = responses.get(key)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, subprocess.CompletedProcess):
            return response
        return _cp(argv, 1, err="stubbed command missing")

    monkeypatch.setattr(cgf.subprocess, "run", _fake_run)


def _ok_git_repo_responses(repo: Path, ahead: str = "0", behind: str = "0") -> dict[tuple[str, tuple[str, ...]], object]:
    repo_str = str(repo.resolve())
    return {
        (repo_str, ("rev-parse", "--is-inside-work-tree")): _cp([], 0, "true\n"),
        (repo_str, ("rev-parse", "--abbrev-ref", "HEAD")): _cp([], 0, "main\n"),
        (repo_str, ("rev-parse", "--abbrev-ref", "@{u}")): _cp([], 0, "origin/main\n"),
        (repo_str, ("fetch", "--quiet", "origin", "main")): _cp([], 0, ""),
        (repo_str, ("rev-list", "--count", "HEAD..@{u}")): _cp([], 0, f"{behind}\n"),
        (repo_str, ("rev-list", "--count", "@{u}..HEAD")): _cp([], 0, f"{ahead}\n"),
    }


def test_seja_priv_detection_skips(monkeypatch, tmp_path, capsys) -> None:
    (tmp_path / "seja-public").mkdir()
    fake_pc = SimpleNamespace(REPO_ROOT=tmp_path, get=lambda key: None)
    monkeypatch.setattr(cgf, "_project_config", fake_pc)

    rc = cgf.main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert "SKIP: harness-dev repo" in out


def test_no_upstream_branch(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    responses = _ok_git_repo_responses(repo)
    repo_key = str(repo.resolve())
    responses[(repo_key, ("rev-parse", "--abbrev-ref", "@{u}"))] = _cp([], 1, err="no upstream")
    _install_git_stub(monkeypatch, responses)

    report = cgf.build_report(str(repo), 5.0)

    assert report["status"] == "ok"
    assert report["repos"][0]["status"] == "no-upstream"


def test_non_git_directory(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "not_git"
    repo.mkdir()
    repo_key = str(repo.resolve())
    responses = {
        (repo_key, ("rev-parse", "--is-inside-work-tree")): _cp([], 1, err="not a git repo"),
    }
    _install_git_stub(monkeypatch, responses)

    report = cgf.build_report(str(repo), 5.0)

    assert report["repos"][0]["status"] == "not-a-git-repo"


def test_fetch_timeout_continues(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    responses = _ok_git_repo_responses(repo, ahead="1", behind="2")
    repo_key = str(repo.resolve())
    responses[(repo_key, ("fetch", "--quiet", "origin", "main"))] = subprocess.TimeoutExpired(
        cmd="git fetch", timeout=5.0
    )
    _install_git_stub(monkeypatch, responses)

    report = cgf.build_report(str(repo), 5.0)
    item = report["repos"][0]

    assert item["fetch"] == "failed"
    assert item["ahead"] == 1
    assert item["behind"] == 2


def test_happy_path_json_output(monkeypatch, tmp_path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    responses = _ok_git_repo_responses(repo, ahead="2", behind="3")
    _install_git_stub(monkeypatch, responses)

    rc = cgf.main(["--json", "--repos", str(repo)])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["repos"][0]["ahead"] == 2
    assert data["repos"][0]["behind"] == 3
    assert "repos" in data
    assert "summary" in data


def test_companion_workspace_detection_distinct_and_same(monkeypatch, tmp_path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "_references" / "project").mkdir(parents=True)
    (root / "_references" / "project" / "conventions.md").write_text("x", encoding="utf-8")

    codebase = tmp_path / "codebase"
    codebase.mkdir()

    fake_pc = SimpleNamespace(REPO_ROOT=root, get=lambda key: str(codebase) if key == "CODEBASE_DIR" else None)
    monkeypatch.setattr(cgf, "_project_config", fake_pc)

    repos, msg = cgf._resolve_repositories(None)
    assert msg is None
    assert len(repos) == 2

    fake_pc_same = SimpleNamespace(REPO_ROOT=root, get=lambda key: str(root) if key == "CODEBASE_DIR" else None)
    monkeypatch.setattr(cgf, "_project_config", fake_pc_same)
    repos_same, msg_same = cgf._resolve_repositories(None)

    assert msg_same is None
    assert len(repos_same) == 1


def test_repos_override_bypasses_auto_discovery(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cgf, "_project_config", None)
    repo = tmp_path / "repo"
    repo.mkdir()

    responses = _ok_git_repo_responses(repo)
    _install_git_stub(monkeypatch, responses)

    report = cgf.build_report(str(repo), 5.0)
    assert report["status"] == "ok"
    assert len(report["repos"]) == 1


def test_partial_fetch_failure_in_companion_mode(monkeypatch, tmp_path) -> None:
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    repo_a.mkdir()
    repo_b.mkdir()

    responses = {}
    responses.update(_ok_git_repo_responses(repo_a, ahead="0", behind="1"))
    responses.update(_ok_git_repo_responses(repo_b, ahead="4", behind="0"))

    key_b = str(repo_b.resolve())
    responses[(key_b, ("fetch", "--quiet", "origin", "main"))] = subprocess.TimeoutExpired(
        cmd="git fetch", timeout=5.0
    )

    _install_git_stub(monkeypatch, responses)

    report = cgf.build_report(f"{repo_a},{repo_b}", 5.0)

    assert len(report["repos"]) == 2
    by_repo = {item["repo"]: item for item in report["repos"]}
    assert by_repo[str(repo_a.resolve())]["fetch"] == "ok"
    assert by_repo[str(repo_b.resolve())]["fetch"] == "failed"


def test_malformed_rev_list_output(monkeypatch, tmp_path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    responses = _ok_git_repo_responses(repo)
    key = str(repo.resolve())
    responses[(key, ("rev-list", "--count", "HEAD..@{u}"))] = _cp([], 0, "not-an-int\n")
    _install_git_stub(monkeypatch, responses)

    rc = cgf.main(["--repos", str(repo)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "warning: non-integer behind count" in captured.err
    assert "behind: unknown" in captured.out


def test_missing_project_config_with_and_without_repos(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cgf, "_project_config", None)

    rc_no_repos = cgf.main([])
    out_no_repos = capsys.readouterr().out
    assert rc_no_repos == 0
    assert "SKIP: project_config unavailable" in out_no_repos

    repo = tmp_path / "repo"
    repo.mkdir()
    responses = _ok_git_repo_responses(repo)
    _install_git_stub(monkeypatch, responses)

    rc_with_repos = cgf.main(["--repos", str(repo)])
    out_with_repos = capsys.readouterr().out
    assert rc_with_repos == 0
    assert "Repo:" in out_with_repos
