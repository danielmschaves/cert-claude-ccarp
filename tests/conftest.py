import json
import shutil
from pathlib import Path

import pytest

from tests.helpers import make_item  # noqa: F401  (re-exported for tests)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def blueprint_path() -> Path:
    return REPO / "blueprint.json"


@pytest.fixture
def tmp_blueprint(tmp_path, blueprint_path):
    """A mutable copy of the real blueprint. Returns (path, mutate_fn)."""
    target = tmp_path / "blueprint.json"
    shutil.copy(blueprint_path, target)

    def mutate(fn):
        raw = json.loads(target.read_text())
        fn(raw)
        target.write_text(json.dumps(raw))
        return target

    return target, mutate


@pytest.fixture
def empty_banks(tmp_path) -> Path:
    d = tmp_path / "banks"
    d.mkdir()
    for n in range(1, 8):
        (d / f"d{n}.json").write_text(json.dumps({"domain": f"d{n}", "items": []}))
    return d


@pytest.fixture
def banks_with(tmp_path):
    """Build a banks dir from {domain: [item, ...]}."""

    def build(mapping):
        d = tmp_path / "banks"
        d.mkdir(exist_ok=True)
        for n in range(1, 8):
            key = f"d{n}"
            (d / f"{key}.json").write_text(
                json.dumps({"domain": key, "items": mapping.get(key, [])})
            )
        return d

    return build
