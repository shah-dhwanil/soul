"""Versioned persona asset bundle with hash-based drift detection."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

PERSONA_VERSION = "wren-2.2"

_ASSETS_DIR = Path(__file__).parent / "assets"
_PROMPT_FILE = "prompt.md"
_MANIFEST_FILE = "manifest.json"


class PersonaDriftError(Exception):
    """Persona assets differ from the manifest or the expected version."""


@dataclass(frozen=True)
class PersonaBundle:
    version: str
    prompt: str
    prompt_sha256: str
    asset_hash: str


def _asset_hash(assets_dir: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        p for p in assets_dir.rglob("*") if p.is_file() and p.name != _MANIFEST_FILE
    )
    blobs = sorted(p.read_bytes() for p in files)
    for blob in blobs:
        digest.update(blob)
    return digest.hexdigest()


def load_persona(assets_dir: Path | None = None) -> PersonaBundle:
    root = assets_dir or _ASSETS_DIR
    prompt_bytes = (root / _PROMPT_FILE).read_bytes()
    manifest_path = root / _MANIFEST_FILE
    version = PERSONA_VERSION
    if manifest_path.exists():
        version = str(
            json.loads(manifest_path.read_text(encoding="utf-8")).get("version", "")
        )
    return PersonaBundle(
        version=version,
        prompt=prompt_bytes.decode("utf-8"),
        prompt_sha256=hashlib.sha256(prompt_bytes).hexdigest(),
        asset_hash=_asset_hash(root),
    )


def assert_no_drift(bundle: PersonaBundle) -> None:
    if bundle.version != PERSONA_VERSION:
        raise PersonaDriftError(
            f"persona version {bundle.version!r} != expected {PERSONA_VERSION!r}"
        )
    manifest = json.loads((_ASSETS_DIR / _MANIFEST_FILE).read_text(encoding="utf-8"))
    if manifest.get("prompt_sha256") != bundle.prompt_sha256:
        raise PersonaDriftError("persona prompt hash differs from manifest")
