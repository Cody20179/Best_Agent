# memory_json.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, List, Union

MemoryInput = Union[str, List[Any]]  # Runner input 可能是 str 或 list（messages/items）

class JsonMemoryStore:
    """
    Very simple persistent memory store:
    - Saves Runner result converted by result.to_input_list()
    - Loads last N items and returns as list for Runner input
    """
    def __init__(self, path: str = "memory.json", keep_last: int = 30):
        self.path = Path(path)
        self.keep_last = keep_last

    def load(self) -> List[Any]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def save(self, items: List[Any]) -> None:
        # keep only last N
        if self.keep_last and len(items) > self.keep_last:
            items = items[-self.keep_last:]
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def append(self, new_items: List[Any]) -> None:
        items = self.load()
        items.extend(new_items)
        self.save(items)
