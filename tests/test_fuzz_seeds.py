"""Replay the atheris seed corpus through the fuzz targets, without atheris installed."""

from pathlib import Path

import fuzz_config_loader
import pytest

CORPUS = Path(__file__).resolve().parent.parent / "fuzz" / "corpus" / "config_loader"
SEEDS = sorted(CORPUS.iterdir())


def test_corpus_is_not_empty():
    """A missing corpus would make the replay below pass vacuously."""
    assert SEEDS


@pytest.mark.parametrize("seed", SEEDS, ids=lambda p: p.name)
def test_config_loader_seed(seed):
    """Every seed loads, or raises only the documented config errors."""
    fuzz_config_loader.fuzz_one(seed.read_bytes())
