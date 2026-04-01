from dataclasses import dataclass, asdict


@dataclass
class BaseProvider:
    title: str
    completed: bool

    def to_dict(self) -> dict:
        return asdict(self)
