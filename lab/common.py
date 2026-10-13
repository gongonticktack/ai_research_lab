import json
import math
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def now():
    return datetime.now(timezone.utc).isoformat()

def validate(record, schema="result"):
    validator = Draft202012Validator(read(ROOT / "schemas" / f"{schema}.schema.json"), format_checker=FormatChecker())
    validator.validate(record)
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite numeric value")
        if isinstance(value, dict):
            for v in value.values(): finite(v)
        if isinstance(value, list):
            for v in value: finite(v)
    finite(record)
    if schema == "result":
        if record["status"] != "completed" and any(v is not None for v in record["metrics"].values()):
            raise ValueError("Incomplete runs cannot report aggregate metrics")
        if record["kind"] == "measured" and record["status"] == "completed":
            if not record["samples"] or any(s["latency_ms"] <= 0 for s in record["samples"]):
                raise ValueError("Measured results need timed samples")
            if not all(record["provenance"].values()) or any(not s["input_sha256"] for s in record["samples"]):
                raise ValueError("Measured results need complete provenance and input hashes")
        if record["status"] == "completed":
            from .metrics import summarize
            expected = summarize(record["samples"])
            for key, value in expected.items():
                actual = record["metrics"][key]
                if (value is None) != (actual is None) or (value is not None and not math.isclose(value, actual, rel_tol=1e-8)):
                    raise ValueError("Aggregate metrics do not match timed samples")
        ids = [s["id"] for s in record["samples"]]
        if len(ids) != len(set(ids)): raise ValueError("Duplicate sample IDs")
    if schema == "experiment":
        ids = [s["id"] for s in record["images"]]
        if len(ids) != len(set(ids)): raise ValueError("Duplicate image IDs")
    return record
