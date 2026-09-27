from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class SpecRequest:
    need: str
    project_path: Path
    today: date
    template: str

    @property
    def project_name(self) -> str:
        return self.project_path.name

    def to_state(self) -> dict[str, str]:
        return {
            "need": self.need,
            "project_path": str(self.project_path),
            "project_name": self.project_name,
            "today": self.today.isoformat(),
            "spec_template": self.template,
        }
