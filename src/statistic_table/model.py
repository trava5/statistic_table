from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RosterPlayer:
    last_name: str
    first_name: str
    registration_number: str
    jersey_number: str
    position: str

    @property
    def birth_year(self) -> int | None:
        if len(self.registration_number) < 4:
            return None
        return int(self.registration_number[-4:])
