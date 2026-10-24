"""S3 check for black-it (Phase 03, reviewer R5): NaN inside real_data. Usage: PYTHONPATH=<clone> python smoke_blackit_nan.py"""
import json
import numpy as np
from black_it.calibrator import Calibrator
from black_it.loss_functions.msm import MethodOfMomentsLoss
from black_it.samplers.halton import HaltonSampler


def model(theta, N, seed):
    rng = np.random.default_rng(seed)
    return (theta[0] + rng.normal(0, 1, N)).reshape(N, 1)


real = model([0.5], 100, 1)
real[10, 0] = np.nan
out = {}
try:
    cal = Calibrator(samplers=[HaltonSampler(batch_size=4)], real_data=real, model=model,
                     parameters_bounds=[[0.0], [1.0]], parameters_precision=[0.01], ensemble_size=1,
                     loss_function=MethodOfMomentsLoss(), random_state=0, n_jobs=1, verbose=False)
    params, losses = cal.calibrate(1)
    out["outcome"] = "ran"
    out["losses"] = [float(x) for x in losses]
    out["all_losses_nan"] = bool(np.all(np.isnan(losses)))
except Exception as e:  # record the library's behaviour, whatever it is
    out["outcome"] = "raised"
    out["error"] = f"{type(e).__name__}: {e}"[:300]
print(json.dumps(out))
