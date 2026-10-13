import math
import statistics

def percentile(values, q):
    if not values: return None
    values = sorted(values)
    i = (len(values)-1) * q
    low, high = math.floor(i), math.ceil(i)
    return values[low] + (values[high]-values[low]) * (i-low)

def mpjpe_mm(predicted, target):
    """MHR70 meters, mid-hip (indices 9,10) relative; no Procrustes alignment."""
    if len(predicted) != 70 or len(target) != 70:
        raise ValueError("Expected 70 MHR joints in the identical order")
    if any(len(j) != 3 or any(not math.isfinite(float(x)) for x in j) for j in predicted + target):
        raise ValueError("Invalid joint coordinates")
    p0 = [(predicted[9][k]+predicted[10][k])/2 for k in range(3)]
    t0 = [(target[9][k]+target[10][k])/2 for k in range(3)]
    errors = [math.sqrt(sum(((p[k]-p0[k])-(t[k]-t0[k]))**2 for k in range(3))) for p,t in zip(predicted,target)]
    return statistics.mean(errors)*1000

def summarize(samples):
    times = [s["latency_ms"] for s in samples]
    errors = [s["mpjpe_mm"] for s in samples if s["mpjpe_mm"] is not None]
    return {"latency_p50_ms": percentile(times,.5), "latency_p95_ms": percentile(times,.95),
            "mpjpe_mm": statistics.mean(errors) if errors else None}
