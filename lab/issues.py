"""One idempotent issue per measured regression; samples never create issues."""
import argparse
import json
import os
import urllib.request
from .common import read

def api(path, method="GET", data=None):
    req=urllib.request.Request("https://api.github.com/"+path,method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization":"Bearer "+os.environ["GITHUB_TOKEN"],"Accept":"application/vnd.github+json",
                 "X-GitHub-Api-Version":"2022-11-28","User-Agent":"ai-research-lab","Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as response: return json.load(response)

def plans(data):
    return [{"marker":f"<!-- ai-research-lab:{c['latest']} -->",
             "title":f"[Lab] Latency regression: {c['latest']}",
             "body":f"<!-- ai-research-lab:{c['latest']} -->\nMeasured p50 latency increased {c['latency_change_percent']}% against {c['previous']}.\n\nDataset: {c['dataset']}. Compare image hashes, software, hardware, and repeated measurements before drawing conclusions."}
            for c in data["comparisons"] if c["regression"]]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--index",default="docs/data/index.json"); p.add_argument("--publish",action="store_true"); a=p.parse_args()
    todo=plans(read(a.index))
    if not a.publish: print(json.dumps(todo,indent=2)); return
    repo=os.environ["GITHUB_REPOSITORY"]
    if not todo: print("No measured regressions; no issue changes."); return
    existing=[]; page=1
    while True:
        batch=api(f"repos/{repo}/issues?state=all&per_page=100&page={page}")
        existing.extend(batch)
        if len(batch)<100: break
        page+=1
    for item in todo:
        match=next((i for i in existing if item["marker"] in (i.get("body") or "") and "pull_request" not in i),None)
        if match: continue  # A user-closed regression remains closed.
        result=api(f"repos/{repo}/issues","POST",{"title":item["title"],"body":item["body"]})
        existing.append(result)
        print(result["html_url"])
if __name__=="__main__": main()
