"""Phase 03 lead re-execution: river.stream.simulate_qa releases each label only once the stream has reached its
maturity time (T3), except the end-of-stream flush. Answers are yielded just before the question whose moment
released them, so they are judged against that next question's time. The first appearance of index i is its question (the clock
moves to its decision time); the second appearance is its answer.
Usage: <river venv python> -I rerun_river.py challenge.csv
"""
import csv, json, sys
import river
from river.stream import simulate_qa
rows = sorted(csv.DictReader(open(sys.argv[1])), key=lambda r: int(r["decision_time"]))
data = [({"t": int(r["decision_time"]), "mat": int(r["label_matures_at"])}, (None if r["label"] == "" else int(r["label"]))) for r in rows]
seen = set(); now = None; asked = 0; buffered = []
res = {"answers_released_before_maturity": 0, "answers_released_at_or_after_maturity": 0,
       "flush_answers": 0, "flush_answers_not_matured_by_last_decision": 0, "flush_answers_with_a_label": 0}
in_flush = False; last_t = data[-1][0]["t"]
for item in simulate_qa(data, moment="t", delay=lambda x, y: x["mat"] - x["t"]):
    i, x = item[0], item[1]
    if i not in seen:
        # answers yielded just before this question were released at this question's moment
        seen.add(i); now = x["t"]; asked += 1
        for xb in buffered:
            if now < xb["mat"]:
                res["answers_released_before_maturity"] += 1
            else:
                res["answers_released_at_or_after_maturity"] += 1
        buffered = []
        if asked == len(data):
            in_flush = True  # every later item is the end-of-stream flush
        continue
    if not in_flush:
        buffered.append(x)
        continue
    if in_flush:
        res["flush_answers"] += 1
        res["flush_answers_not_matured_by_last_decision"] += int(x["mat"] > last_t)
        res["flush_answers_with_a_label"] += int(data[i][1] is not None)
res.update({"river_version": river.__version__, "questions": asked})
print("RESULTS_JSON " + json.dumps(res, sort_keys=True))
