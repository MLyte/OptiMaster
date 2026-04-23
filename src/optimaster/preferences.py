from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PreferenceStore:
    path: Path

    def load(self) -> dict[str, float]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in raw.get("preset_bias", {}).items()}

    def save_note(self, preset_name: str, rating: int) -> None:
        rating = max(1, min(5, int(rating)))
        data = {"notes": [], "preset_stats": {}}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))

        notes = list(data.get("notes", []))
        stats = dict(data.get("preset_stats", {}))

        note = {"preset": preset_name, "rating": rating}
        notes.append(note)

        current = stats.get(preset_name, {"count": 0, "sum": 0})
        count = int(current.get("count", 0)) + 1
        total = int(current.get("sum", 0)) + rating
        stats[preset_name] = {"count": count, "sum": total}

        preset_bias = {
            name: round(((entry["sum"] / max(entry["count"], 1)) - 3.0) * 2.0, 2)
            for name, entry in stats.items()
        }

        payload = {
            "notes": notes,
            "preset_stats": stats,
            "preset_bias": preset_bias,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
