from pathlib import Path

from optimaster.cli import _batch_target_dir, cmd_optimize_batch
from optimaster.config import AppConfig
from optimaster.models import OptimizationMode, OptimizationSession


def test_batch_target_dir_keeps_first_stem_and_disambiguates_duplicates() -> None:
    seen: dict[str, int] = {}
    output_dir = Path("renders")

    first = _batch_target_dir(output_dir, Path("mix.wav"), 1, seen)
    second = _batch_target_dir(output_dir, Path("mix.wav"), 2, seen)
    third = _batch_target_dir(output_dir, Path("MIX.flac"), 3, seen)

    assert first == output_dir / "mix"
    assert second == output_dir / "mix-02"
    assert third == output_dir / "MIX-03"


def test_cmd_optimize_batch_uses_distinct_output_dirs(monkeypatch, capsys) -> None:
    calls: list[Path] = []

    class FakeService:
        def __init__(self, config: AppConfig) -> None:
            self.config = config

        def optimize(self, input_file: str | Path, output_dir: str | Path, mode: OptimizationMode | None = None):
            calls.append(Path(output_dir))
            return OptimizationSession(
                session_id="session-1",
                mode=mode or OptimizationMode.BALANCED,
                analysis=None,  # type: ignore[arg-type]
                candidates=[],
            )

    monkeypatch.setattr("optimaster.cli.load_config", lambda _path: AppConfig())
    monkeypatch.setattr("optimaster.cli.EngineService", FakeService)

    exit_code = cmd_optimize_batch(
        input_files=["mix.wav", "mix.wav", "MIX.flac"],
        output_dir="renders",
        mode="balanced",
        config_path=None,
    )

    assert exit_code == 0
    assert calls == [Path("renders/mix"), Path("renders/mix-02"), Path("renders/MIX-03")]
    assert "Running batch on 3 file(s)..." in capsys.readouterr().out
