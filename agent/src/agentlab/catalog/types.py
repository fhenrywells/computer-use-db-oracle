from dataclasses import dataclass
from typing import Any


@dataclass
class TypedAction:
    type: str
    args: dict[str, Any]

