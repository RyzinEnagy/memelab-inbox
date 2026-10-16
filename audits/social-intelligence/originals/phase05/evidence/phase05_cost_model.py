"""Phase 05 illustrative operating-cost calculations ONLY; does not invoke Memelab or network."""
from decimal import Decimal, ROUND_HALF_UP
import json

D = Decimal
DAYS = 30
X_POST_PRICE = D('0.005')
X_SHARE = D('0.50')
CLASSIFIED_SHARE = D('0.30')
IN = D('1800')
OUT = D('250')
INPUT_PER_MILLION = D('0.10')
OUTPUT_PER_MILLION = D('0.50')


def scenario(posts_per_day, helius_monthly_usd):
    posts = D(str(posts_per_day * DAYS))
    x_reads = posts * X_SHARE
    calls = posts * CLASSIFIED_SHARE
    x = x_reads * X_POST_PRICE
    llm = calls * (IN * INPUT_PER_MILLION + OUT * OUTPUT_PER_MILLION) / D('1000000')
    total = x + llm + D(str(helius_monthly_usd))
    money = lambda n: str(n.quantize(D('0.01'), rounding=ROUND_HALF_UP))
    return {"posts_day": posts_per_day, "posts_month": int(posts), "charged_x_reads": int(x_reads),
            "llm_calls": int(calls), "x_usd": money(x), "llm_usd": money(llm),
            "helius_usd": money(D(str(helius_monthly_usd))), "total_usd": money(total)}


scenarios = [scenario(100, 0), scenario(1000, 0), scenario(10000, 49)]
assert [(s['total_usd']) for s in scenarios] == ['7.77', '77.75', '826.45']
assert [(s['x_usd']) for s in scenarios] == ['7.50', '75.00', '750.00']
assert [(s['llm_usd']) for s in scenarios] == ['0.27', '2.75', '27.45']
print(json.dumps({"status": "PASS", "description": "synthetic arithmetic, no API or engine runtime", "scenarios": scenarios}, indent=2))
