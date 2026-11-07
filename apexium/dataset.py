"""Dataset with portable exports and explicit data provenance."""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Dataset:
    records: list[dict[str, Any]]
    source: str
    url: str
    fetched_at: str
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.records[index]

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.records, indent=indent, ensure_ascii=False, default=str)

    def to_csv(self) -> str:
        stream = io.StringIO(newline="")
        fields = list(dict.fromkeys(key for item in self.records for key in item))
        if not fields:
            return ""
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in self.records:
            writer.writerow({key: _cell(value) for key, value in record.items()})
        return stream.getvalue()

    def to_pandas(self):
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError("Install the pandas extra: pip install apexium-f1[pandas]") from exc
        return pd.DataFrame(self.records)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        extension = path.suffix.lower()
        if extension == ".json":
            path.write_text(self.to_json(), encoding="utf-8")
        elif extension == ".csv":
            path.write_text(self.to_csv(), encoding="utf-8")
        elif extension == ".parquet":
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise ImportError("Install the parquet extra: pip install apexium-f1[parquet]") from exc
            pq.write_table(pa.Table.from_pylist(self.records) if self.records else pa.table({}), path)
        else:
            raise ValueError("Expected a .json, .csv or .parquet output path")
        return path


def _cell(value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
