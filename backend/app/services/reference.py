"""Load the challenge reference data used to validate CMS content."""
from functools import lru_cache
import json
from pathlib import Path


REFERENCE_PATH = Path(__file__).resolve().parents[1] / "api" / "v1" / "files" / "reference.json"


@lru_cache
def reference_data() -> dict:
    with REFERENCE_PATH.open(encoding="utf-8") as reference_file:
        return json.load(reference_file)


def allowed_sections() -> set[str]:
    return set(reference_data()["sections"])


def allowed_categories() -> set[str]:
    return set(reference_data()["categories"])


def allowed_languages() -> set[str]:
    return set(reference_data()["languages"])


def required_artwork_types() -> set[str]:
    """Artwork variants specified by the reference contract for episodes."""
    return set(reference_data()["artwork_specs"])
