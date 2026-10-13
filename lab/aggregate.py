import argparse
from collections import defaultdict
from pathlib import Path
from .common import read, write, validate, now
from .metrics import summarize

def aggregate(directory):
    runs = [validate(read(p)) for p in sorted(Path(directory).glob("*.json"))]
    ids = [r["run_id"] for r in runs]
    if len(ids) != len(set(ids)): raise ValueError("Duplicate run IDs")
    groups = defaultdict(list)
    for r in runs:
        if r["kind"] == "measured" and r["status"] == "completed":
            # Protocol/hardware/checkpoints must match before comparing runs.
            input_set=tuple(sorted(s["input_sha256"] for s in r["samples"]))
            key = (r["dataset"], r["model"], r["protocol"], r["environment"]["gpu"], r["provenance"]["checkpoint_sha256"],
                   r["provenance"]["mhr_sha256"],r["environment"]["torch"],r["environment"]["python"],input_set)
            groups[key].append(r)
    comparisons = []
    for key, series in groups.items():
        series.sort(key=lambda r:r["created_at"])
        if len(series)<2: continue
        previous, latest = series[-2:]
        before, after = previous["metrics"]["latency_p50_ms"], latest["metrics"]["latency_p50_ms"]
        if before is None or after is None or before <= 0: continue
        delta = (after/before-1)*100
        comparisons.append({"dataset":key[0],"previous":previous["run_id"],"latest":latest["run_id"],
                            "latency_change_percent":round(delta,2),"regression":delta>20,
                            "note":"Descriptive only; image set, software and repeated-run variance must be reviewed."})
    return {"generated_at":now(),"runs":runs,"measured_count":sum(r["kind"]=="measured" and r["status"]=="completed" for r in runs),
            "sample_count":sum(r["kind"]=="sample" for r in runs),"comparisons":comparisons}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--results",default="results"); p.add_argument("--output",default="docs/data/index.json")
    a=p.parse_args(); data=aggregate(a.results); write(a.output,data)
    lines=["# 実験集計",f"集計時刻 (UTC): {data['generated_at']}",f"実測完了: {data['measured_count']} / サンプル: {data['sample_count']}"]
    if not data["measured_count"]: lines.append("実測結果はまだありません。サンプルは性能評価に使いません。")
    for c in data["comparisons"]: lines.append(f"- {c['latest']}: latency変化 {c['latency_change_percent']}% (記述的比較)")
    Path(a.output).with_suffix(".md").write_text("\n\n".join(lines)+"\n",encoding="utf-8")
if __name__ == "__main__": main()
