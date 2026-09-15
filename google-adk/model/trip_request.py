from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TripRequest:
    origin: str
    destination: str
    departure_date: date
    return_date: date
    today: date

    def to_state(self) -> dict[str, str]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date.isoformat(),
            "return_date": self.return_date.isoformat(),
            "today": self.today.isoformat(),
        }
