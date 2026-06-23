from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("Pic" + "Pak", "pic" + "pak", "PIC" + "PAK")
SKIP_PARTS = {".git", ".venv", ".pytest_cache", "__pycache__", "data"}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".dockerfile",
}


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "LICENSE"}


def fail(message: str) -> None:
    print(f"release guard failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_branding() -> None:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        rel_text = str(rel)
        if any(token in rel_text for token in FORBIDDEN):
            hits.append(rel_text)
            continue
        if path.is_file() and is_text_file(path):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in FORBIDDEN:
                if token in text:
                    hits.append(f"{rel_text}: contains old brand token")
                    break
    if hits:
        fail("old Ditherloom predecessor branding found:\n" + "\n".join(hits[:50]))


def check_licenses() -> None:
    license_path = ROOT / "LICENSE.md"
    notices_path = ROOT / "THIRD_PARTY_NOTICES.md"
    if not license_path.exists():
        fail("LICENSE.md is missing")
    if not notices_path.exists():
        fail("THIRD_PARTY_NOTICES.md is missing")
    license_text = license_path.read_text(encoding="utf-8")
    notices_text = notices_path.read_text(encoding="utf-8")
    for required in ("Polycom 1", "Neil Cameron", "third-party"):
        if required not in license_text:
            fail(f"LICENSE.md missing required text: {required}")
    for required in ("FastAPI", "Uvicorn", "Pillow", "Eclipse Paho MQTT", "python-multipart", "Open-Meteo"):
        if required not in notices_text:
            fail(f"THIRD_PARTY_NOTICES.md missing required component: {required}")


def check_no_generated_cache_files() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    generated = [
        path
        for path in tracked
        if "__pycache__" in Path(path).parts or Path(path).suffix in {".pyc", ".pyo"}
    ]
    if generated:
        fail("generated Python cache files must not be committed:\n" + "\n".join(generated[:50]))


def main() -> None:
    check_branding()
    check_licenses()
    check_no_generated_cache_files()
    print("release guards passed")


if __name__ == "__main__":
    main()
