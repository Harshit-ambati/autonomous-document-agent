"""Package an explicit allowlist of source and verified live examples, excluding secrets."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = []
    for directory in ("app", "scripts", "tests", "examples", "evals", "docs", ".github"):
        sources.extend(
            path
            for path in (ROOT / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.name not in {"VIDEO_SCRIPT.md", "DEMO.md"}
        )
    sources.extend(
        ROOT / name
        for name in (
            "README.md",
            ".env.example",
            ".gitignore",
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-lock.txt",
        )
    )
    samples = [
        ROOT / "outputs" / "demo" / f"{case}.{extension}"
        for case in ("standard", "complex")
        for extension in ("docx", "json")
    ]
    for path in [*sources, *samples]:
        if not path.is_file():
            raise SystemExit(f"Missing submission input: {path.relative_to(ROOT)}")
    target = ROOT / "submission.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in sorted(sources):
            archive.write(path, str(path.relative_to(ROOT)))
        for path in samples:
            archive.write(path, f"sample_outputs/{path.name}")
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Archive integrity check failed")
        assert all(not name.endswith("/.env") and name != ".env" for name in archive.namelist())
        print(
            f"Created {target.name}: {len(archive.namelist())} files; .env, virtual environment and QA files excluded"
        )


if __name__ == "__main__":
    main()
