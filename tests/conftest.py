from pathlib import Path

import pytest

from mechanism_generator.omts import load_document


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def task_document():
    return load_document(ROOT / "examples/omts/three_point.omts.yaml")


@pytest.fixture
def future_document():
    return load_document(ROOT / "examples/omts/synchronized_line.omts.yaml")
