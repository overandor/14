from __future__ import annotations

import subprocess

import pytest

from repo_factory.creator import NamingStrategy, RepositoryCreator


def test_create_sequential_repositories(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, check):  # noqa: ANN001
        calls.append((tuple(args), check))
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    target_root = tmp_path / "repos"
    creator = RepositoryCreator(root_directory=target_root)

    specs = creator.create_repositories(
        count=3,
        naming=NamingStrategy.SEQUENTIAL,
        prefix="unit",
        start_index=5,
        initialize_git=True,
    )

    assert [spec.name for spec in specs] == ["unit-05", "unit-06", "unit-07"]
    for spec in specs:
        repo_path = target_root / spec.name
        assert repo_path.exists()
        assert (repo_path / "README.md").exists()
        assert (repo_path / ".gitignore").exists()

    assert len(calls) == 3


def test_random_naming_bounds(tmp_path):
    creator = RepositoryCreator(root_directory=tmp_path / "repos")
    with pytest.raises(ValueError):
        creator.create_repositories(count=0)
    with pytest.raises(ValueError):
        creator.create_repositories(count=101, naming=NamingStrategy.RANDOM)
