from pathlib import Path

from optimaster.preferences import PreferenceStore


def test_preference_store_creates_bias_file(tmp_path: Path) -> None:
    store = PreferenceStore(tmp_path / "preferences.json")
    store.save_note("safe_limit", 5)
    store.save_note("safe_limit", 4)
    store.save_note("gentle_glue", 2)

    bias = store.load()
    assert bias["safe_limit"] > 0
    assert bias["gentle_glue"] < 0
