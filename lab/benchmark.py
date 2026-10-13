import argparse
import hashlib
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path
from .common import read, write, validate, now
from .metrics import summarize, mpjpe_mm

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def run(config):
    validate(config,"experiment")
    record={"schema_version":"1.0","run_id":"run-"+uuid.uuid4().hex[:12],"created_at":now(),"kind":"measured",
            "status":"blocked","model":"sam-3d-body-dinov3","dataset":config["dataset"],
            "protocol":"mhr70-pelvis-relative-meters/full-image/no-detector/no-fov/warmup-1/repeats-"+str(config["repeats"]),
            "environment":{"python":platform.python_version(),"gpu":"unavailable","torch":None},
            "provenance":{"upstream_commit":None,"checkpoint_sha256":None,"mhr_sha256":None,"config_sha256":hashlib.sha256(__import__('json').dumps(config,sort_keys=True).encode()).hexdigest()},
            "samples":[],"metrics":{"latency_p50_ms":None,"latency_p95_ms":None,"mpjpe_mm":None},"notes":[],"artifacts":[]}
    missing=[str(config[k]) for k in ("upstream","checkpoint","mhr") if not Path(config[k]).exists()]
    for s in config["images"]:
        if not Path(s["path"]).is_file(): missing.append(s["path"])
    if missing:
        record["notes"]=["Missing required paths: "+", ".join(missing)]; return validate(record)
    try:
        import torch
        import numpy as np
        if not torch.cuda.is_available():
            record["notes"]=["CUDA is required by the official estimator; CPU fallback is not supported."]; return validate(record)
        record["environment"].update(gpu=torch.cuda.get_device_name(0),torch=torch.__version__)
        record["provenance"].update(checkpoint_sha256=sha256(config["checkpoint"]),mhr_sha256=sha256(config["mhr"]),
            upstream_commit=subprocess.check_output(["git","-C",config["upstream"],"rev-parse","HEAD"],text=True).strip())
        sys.path.insert(0,str(Path(config["upstream"]).resolve()))
        from sam_3d_body import load_sam_3d_body, SAM3DBodyEstimator
        model,cfg=load_sam_3d_body(checkpoint_path=config["checkpoint"],mhr_path=config["mhr"],device="cuda")
        estimator=SAM3DBodyEstimator(model,cfg)  # Single-person images: full-image bounding box.
        for image in config["images"]:
            # Warm up each input once; exclude initialization, file hashing and export from timings.
            estimator.process_one_image(str(Path(image["path"]).resolve()))
            durations=[]
            for _ in range(config["repeats"]):
                torch.cuda.synchronize(); started=time.perf_counter()
                outputs=estimator.process_one_image(str(Path(image["path"]).resolve()))
                torch.cuda.synchronize(); durations.append((time.perf_counter()-started)*1000)
            if len(outputs)!=1: raise ValueError("Single-person benchmark expects exactly one prediction")
            prediction=outputs[0]
            error=None
            if image.get("ground_truth"):
                gt=read(image["ground_truth"])
                if gt["joint_layout"]!="mhr70" or gt["units"]!="meters": raise ValueError("GT requires mhr70 in meters")
                error=mpjpe_mm(prediction["pred_keypoints_3d"].tolist(),gt["joints"])
            # One sample per timed repeat; avoid hiding variance behind an average.
            for i,duration in enumerate(durations):
                record["samples"].append({"id":image["id"]+f"-repeat-{i}","input_sha256":sha256(image["path"]),"latency_ms":duration,"mpjpe_mm":error})
            if config["export_mesh"]:
                relative=f"meshes/{record['run_id']}-{image['id']}.json"
                write(Path(config["output"])/relative,{"kind":"measured","vertices":np.asarray(prediction["pred_vertices"]).tolist(),"faces":np.asarray(estimator.faces).tolist()})
                record["artifacts"].append(relative)
        record["metrics"]=summarize(record["samples"]); record["status"]="completed"
        record["notes"]=["Timing includes image decoding and full estimator call; model setup/export excluded. Default FOV, no detector. GT absent means MPJPE=null."]
    except ImportError as exc:
        record["notes"]=["Dependency unavailable: "+str(exc)]
    except Exception as exc:
        record["status"]="failed"; record["metrics"]={k:None for k in record["metrics"]}; record["notes"]=[type(exc).__name__+": "+str(exc)]
    return validate(record)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",default="experiments/sam3d.local.json"); a=p.parse_args()
    config=read(a.config); result=run(config); write(Path(config["output"])/(result["run_id"]+".json"),result)
    print(result["status"]+": "+"; ".join(result["notes"]))
    if result["status"]!="completed": raise SystemExit(2)
if __name__=="__main__": main()
