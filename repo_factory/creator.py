from __future__ import annotations

import os
import re
import secrets
import string
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List


class NamingStrategy(str, Enum):
    SEQUENTIAL = "sequential"
    RANDOM = "random"


LAUNCH_TARGETS = (
    {
        "label": "Launch on Google Colab",
        "url": "https://colab.research.google.com/",
    },
    {
        "label": "Launch on Hugging Face Spaces",
        "url": "https://huggingface.co/spaces",
    },
    {
        "label": "Launch on Replicate",
        "url": "https://replicate.com/create",
    },
    {
        "label": "Launch on Modal",
        "url": "https://modal.com/",
    },
    {
        "label": "Launch on Vercel",
        "url": "https://vercel.com/new",
    },
    {
        "label": "Launch on Render",
        "url": "https://dashboard.render.com/",
    },
    {
        "label": "Launch on Netlify",
        "url": "https://app.netlify.com/start",
    },
)


@dataclass(frozen=True)
class RepositorySpec:
    name: str
    path: Path


class RepositoryCreator:
    """Create initialized Git repositories from deterministic specs."""

    def __init__(
        self,
        root_directory: str | os.PathLike[str] = "generated_repos",
        git_binary: str = "git",
    ) -> None:
        self.root = Path(root_directory)
        self.git_binary = git_binary
        self.root.mkdir(parents=True, exist_ok=True)

    def create_repositories(
        self,
        count: int,
        naming: NamingStrategy = NamingStrategy.SEQUENTIAL,
        prefix: str = "project",
        start_index: int = 1,
        initialize_git: bool = True,
    ) -> List[RepositorySpec]:
        if count < 1:
            raise ValueError("count must be positive")
        if naming == NamingStrategy.SEQUENTIAL and count > 1000:
            raise ValueError("sequential naming limited to 1000 repositories per invocation")
        if naming == NamingStrategy.RANDOM and count > 100:
            raise ValueError("random naming limited to 100 repositories per invocation")

        names = list(self._generate_names(count, naming, prefix, start_index))
        if len(set(names)) != len(names):
            raise ValueError("naming configuration produced duplicate repositories")

        specs = [RepositorySpec(name=name, path=self.root / name) for name in names]

        for spec in specs:
            self._create_single(spec, initialize_git=initialize_git)

        return specs

    def _generate_names(
        self,
        count: int,
        naming: NamingStrategy,
        prefix: str,
        start_index: int,
    ) -> Iterable[str]:
        if naming == NamingStrategy.SEQUENTIAL:
            for offset in range(count):
                candidate = f"{prefix}-{start_index + offset:02d}"
                yield self._sanitize(candidate)
        elif naming == NamingStrategy.RANDOM:
            alphabet = string.ascii_lowercase + string.digits
            for _ in range(count):
                suffix = "".join(secrets.choice(alphabet) for _ in range(8))
                candidate = f"{prefix}-{suffix}"
                yield self._sanitize(candidate)
        else:
            raise ValueError(f"unsupported naming strategy: {naming}")

    def _create_single(self, spec: RepositorySpec, initialize_git: bool) -> None:
        spec.path.mkdir(parents=True, exist_ok=False)
        if initialize_git:
            self._init_git_repository(spec.path)
        self._write_readme(spec.path, spec.name)
        self._write_gitignore(spec.path)

    def _init_git_repository(self, path: Path) -> None:
        subprocess.run([self.git_binary, "init", str(path)], check=True)

    def _write_readme(self, path: Path, repo_name: str) -> None:
        launch_section = "\n".join(
            f"- [{target['label']}]({target['url']})" for target in LAUNCH_TARGETS
        )
        readme = f"""# {repo_name}\n\n"""
        readme += "This repository was generated automatically.\n\n"
        readme += "## Launch Targets\n"
        readme += f"{launch_section}\n"
        readme += "\n"
        readme += "## Usage\n"
        readme += "Describe your project here.\n"
        (path / "README.md").write_text(readme, encoding="utf-8")

    def _write_gitignore(self, path: Path) -> None:
        contents = """# Python caches\n__pycache__/\n*.py[cod]\n\n# Virtual environments\n.venv/\nvenv/\nENV/\n\n# Editors\n.vscode/\n.idea/\n"""
        (path / ".gitignore").write_text(contents, encoding="utf-8")

    @staticmethod
    def _sanitize(value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
        sanitized = sanitized.strip(".-")
        if not sanitized:
            raise ValueError("sanitized repository name is empty")
        return sanitized
