# Second reviewer rerun: statsmodels 0.15.0 wheel (tsa/regime_switching identical to pin aa61cc14, git diff --stat empty).
import warnings, numpy as np, statsmodels
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from statsmodels.stats.multitest import multipletests
warnings.simplefilter("ignore")
rng = np.random.default_rng(11)
# own series: 1,200 points, regime shift in the last 400
y = np.r_[rng.normal(0.0, 0.05, 800), rng.normal(0.04, 0.06, 400)]
cut = 800
m_tr = MarkovRegression(y[:cut], k_regimes=2, switching_variance=True).fit(disp=False)
m_full = MarkovRegression(y, k_regimes=2, switching_variance=True).fit(disp=False)
# filter the FULL series with TRAIN-only params, compare with filtered on the train-only series
f_trunc = MarkovRegression(y[:cut], k_regimes=2, switching_variance=True).filter(m_tr.params).filtered_marginal_probabilities[:, 0]
f_ext = MarkovRegression(y, k_regimes=2, switching_variance=True).filter(m_tr.params).filtered_marginal_probabilities[:cut, 0]
s_ext = MarkovRegression(y, k_regimes=2, switching_variance=True).smooth(m_tr.params).smoothed_marginal_probabilities[:cut, 0]
f_full = m_full.filtered_marginal_probabilities[:cut, 0]
print("statsmodels", statsmodels.__version__)
print("filter, train params, train-only vs extended series: max abs diff", float(np.max(np.abs(f_trunc - f_ext))))
print("smooth, train params, extended vs filter on train rows: max abs diff", round(float(np.max(np.abs(s_ext - f_ext))), 4))
print("filter, full-sample params vs train params on train rows: max abs diff", round(float(np.max(np.abs(f_full - f_trunc))), 4), "(label switching possible)", round(float(np.max(np.abs((1 - f_full) - f_trunc))), 4))
try:
    m_full.predict(start=len(y), end=len(y) + 5); print("out-of-sample predict: allowed")
except NotImplementedError:
    print("out-of-sample predict: NotImplementedError")
print("holm", multipletests([0.012, 0.030, 0.041], method="holm")[1].round(4).tolist())
