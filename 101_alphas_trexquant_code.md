# 101 Alphas → Trexquant Code (All 101)

Runnable Trexsim translations of all 101 formulaic alphas, each with a 1–10 score and comments. Paste the Setup block (Section 0) once, then any alpha below. **Never paste `import`** — TrexSim errors with `'import' is not allowed.`; `np` is already in scope.

- **`alpha` is a stock × date matrix.** Positions are demeaned + booksized by the simulator.
- **Scores (1–10)** are my rough prior on how each might do as a *standalone* qualifying alpha
  (IR > 0.07, low turnover-adjusted) in this US medium-frequency setup. They are opinions, not
  backtests — treat them as a screening order, not gospel.
- **`vwap` is a proxy.** The dataset has no daily VWAP (only `vwap_first_hour` / `vwap_last_hour`),
  so I use the typical price `(high+low+close)/3`. Every vwap-based alpha inherits this risk.

---

---

## Lookback (slow mode) — how the numbers below were derived

Every alpha now carries a **Req. lookback** line. It is the **minimum window** slow mode needs to
compute the *final* day correctly: the sum of nested time-series depths along the deepest path, **+1**.
(Per the tutorial, `ts_mean(ret1, 30)` needs **31**, not 30 — `ret1` costs one extra prior day.)

Offsets used: `ts_*(x,d)`, `decay_linear`, `product`, `ts_argmax/min`, `covariance(x,y,d)` add `d-1`;
`ts_corr_binary(x,y,d)` adds `d-1` on top of the deeper of its two inputs; `ts_delay(x,k)` adds `k`;
`delta(x,d)` adds `d`; `ret1`/`returns` add `1`; `adv(d)=ts_mean(volume,d)` adds `d-1`; cross-sectional
(`rank`, `cs_*`, `scale`) and element-wise ops add `0`.

**Buffer:** the `use ~Nd` figure adds **+5 days** (**+10** for the 100d+ alphas). Give the buffer —
NaN gaps (holidays/halts/young listings) eat into `corr`/`std`/`decay` windows, and rolling operators
warm up over their first window. Buffer only fixes *insufficient lookback*; it does **not** fix forward
bias or corporate-adjustment gaps (separate fast≠slow causes).

**Watch these (250d+):** #19, #39, #48, #52 (~250), #32 (~235), #71 (~225), #24/#36/#37 (~200),
plus the `adv150`/`adv180` template alphas (#61, #63, #79, ...).

## 0. Setup — paste this once (top of the alpha editor)

Do not add `import numpy as np` or any other `import`. `np` is preloaded.

```python
# np is preloaded. Do not import — TrexSim rejects `import`.

# ---------- data proxies ----------
vwap    = (high + low + close) / 3.0      # NO daily vwap in dataset → typical-price proxy
returns = ret1                            # daily close-to-close return (fractional)

def adv(d):                               # avg daily volume (shares)
    # Paper defines adv{d} as avg daily *dollar* volume. Share-volume keeps the many
    # `volume/adv` and `adv<volume` comparisons dimensionally sane. Swap to
    # ts_mean(close*volume, d) if you want the literal dollar-volume version.
    return ts_mean(volume, d)

# ---------- paper operators that aren't built in ----------
def rank(x):                              # paper rank = cross-sectional, in [0,1]
    return cs_rank(x) - 1.0               # cs_rank returns [1,2]; shift to [0,1]

def delta(x, d):                          # paper delta = LAG-d diff (NOT ts_diff for d>1)
    return x - ts_delay(x, d)

def signedpower(x, a):
    return np.sign(x) * (np.abs(x) ** a)

def scale(x, a=1.0):                      # per-day rescale so sum(|x|)=a  (NOT cs_scale!)
    s = np.nansum(np.abs(x), axis=0, keepdims=True)
    s = np.where(s == 0, np.nan, s)
    return a * x / s

def covariance(x, y, d):                  # cov = corr * std_x * std_y
    return ts_corr_binary(x, y, d) * ts_std(x, d) * ts_std(y, d)

def product(x, d):
    out = np.full(x.shape, np.nan)
    for t in range(d - 1, x.shape[1]):
        out[:, t] = np.nanprod(x[:, t - d + 1:t + 1], axis=1)
    return out

def decay_linear(x, d):                   # linear-decay weighted MA, weights d..1 (recent=d)
    w = np.arange(d, 0, -1, dtype=float)
    out = np.zeros(x.shape); den = np.zeros(x.shape)
    for k in range(d):
        v = ts_delay(x, k); m = np.isfinite(v)
        out = out + np.where(m, v * w[k], 0.0)
        den = den + np.where(m, w[k], 0.0)
    return np.where(den > 0, out / den, np.nan)

def ts_argmax(x, d):                      # window index of max: today=d-1 ... oldest=0
    best = np.full(x.shape, -np.inf); idx = np.full(x.shape, np.nan)
    for k in range(d):
        v = ts_delay(x, k); take = v > best
        best = np.where(take, v, best); idx = np.where(take, d - 1 - k, idx)
    return np.where(np.isfinite(best), idx, np.nan)

def ts_argmin(x, d):
    best = np.full(x.shape, np.inf); idx = np.full(x.shape, np.nan)
    for k in range(d):
        v = ts_delay(x, k); take = v < best
        best = np.where(take, v, best); idx = np.where(take, d - 1 - k, idx)
    return np.where(np.isfinite(best), idx, np.nan)
```

**Operator map used throughout:** `correlation→ts_corr_binary`, `stddev→ts_std`, `sum→ts_sum`,
`sum(x,d)/d→ts_mean(x,d)`, `min/max→ts_min/ts_max`, `Ts_Rank→ts_rank`, `delay→ts_delay`,
`sign/abs/log→np.sign/np.abs/np.log`, `x?y:z→np.where`.

**Conventions in the code below:**
- **Non-integer day args are floored to `int`** (the paper says `ts_{O}(x,d)` uses `floor(d)`), e.g.
  `decay_linear(x, 7.89)` → `decay_linear(x, 7)`. This matters for alphas 58+.
- **`IndClass.sector / industry / subindustry`** → the `sector` / `industry` / `subindustry`
  variables via `cs_indneut(x, group)`.
- **Blended weights that collapse** (e.g. `vwap*0.73 + vwap*(1-0.73) == vwap`) are simplified, noted
  inline.
- **Boolean `<` alphas** return {0,1} (cast to float) or, with `* -1`, {0,−1} — the paper's design;
  the simulator demeans them.

> Alphas 58–99 mostly share one template:
> `Ts_Rank(decay_linear(correlation(IndNeutralize(price), adv/vol)))`. They're real production-style
> alphas but carry **fitted decimal constants** (overfit risk), **industry data**, and **long
> lookbacks** (adv180 + windows → 200+ days). Screen hard in slow mode.

---

## Alpha #1 — score 4/10
*Argmax over 5 days of squared (down-day vol / up-day price), ranked.*
```python
inner = np.where(returns < 0, ts_std(returns, 20), close)
alpha = rank(ts_argmax(signedpower(inner, 2.0), 5)) - 0.5
```

> **Req. lookback ≈ 25d** (minimum for the last day) · use ~30d with buffer.
Obscure construction — it's really "when did volatility/price peak recently." Mixed units inside the
`where` (vol vs price) make it hard to reason about; low turnover but faint edge. `-0.5` centers the
[0,1] rank, which my `rank` helper preserves.

## Alpha #2 — score 6/10
*Reversion: volume-change rank vs intraday-return rank, anti-correlated.*
```python
alpha = -1 * ts_corr_binary(rank(delta(np.log(volume), 2)), rank((close - open) / open), 6)
```

> **Req. lookback ≈ 8d** (minimum for the last day) · use ~13d with buffer.
Clean price-volume reversion, a classic that tends to carry real signal. `np.log(volume)` is safe
(volume > 0); it's monotonic so the rank is unchanged vs `at_signlog`.

## Alpha #3 — score 6/10
*Reversion: rank(open) vs rank(volume), anti-correlated over 10d.*
```python
alpha = -1 * ts_corr_binary(rank(open), rank(volume), 10)
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Cheap, robust, low turnover. One of the more dependable price-volume alphas.

## Alpha #4 — score 5/10
*Time-series reversion on the cross-sectional rank of the low price.*
```python
alpha = -1 * ts_rank(rank(low), 9)
```

> **Req. lookback ≈ 9d** (minimum for the last day) · use ~14d with buffer.
Short-horizon reversion on relative lows. Works, but weak on its own and correlated with other
low/close reversion alphas.

## Alpha #5 — score 5/10
*Open vs 10d-VWAP, tempered by |close−vwap|.*
```python
alpha = rank(open - ts_mean(vwap, 10)) * (-1 * np.abs(rank(close - vwap)))
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Decent reversion idea, but **double vwap-proxy exposure** — most sensitive alpha here to the missing
daily VWAP. Validate against the hourly-VWAP blend before trusting it.

## Alpha #6 — score 6/10
*Reversion: −correlation(open, volume, 10).*
```python
alpha = -1 * ts_corr_binary(open, volume, 10)
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Sibling of #3 without the ranks. Solid, cheap; likely > 50% correlated with #3, so keep only the
better of the two for the pool.

## Alpha #7 — score 5/10
*On high-volume days, fade recent price moves; else short.*
```python
d7   = delta(close, 7)
cond = adv(20) < volume
alpha = np.where(cond, (-1 * ts_rank(np.abs(d7), 60)) * np.sign(d7), -1.0)
```

> **Req. lookback ≈ 67d** (minimum for the last day) · use ~72d with buffer.
Conditional reversion gated by a volume spike. The `-1` fallback pushes a flat short on quiet days
(fine after demeaning). Turnover is on the higher side.

## Alpha #8 — score 5/10
*Reversal of the 5d (open×returns) sum vs its value 10d ago.*
```python
term  = ts_sum(open, 5) * ts_sum(returns, 5)
alpha = -1 * rank(term - ts_delay(term, 10))
```

> **Req. lookback ≈ 16d** (minimum for the last day) · use ~21d with buffer.
Momentum-reversal on a compound term; moderate. Mixing `open` (price) with `returns` makes the units
a bit muddy but it's rank-wrapped so scale is tamed.

## Alpha #9 — score 4/10
*Keep 1d move if the 5d run is monotone up or down, else fade it.*
```python
d1 = delta(close, 1)
alpha = np.where(ts_min(d1, 5) > 0, d1, np.where(ts_max(d1, 5) < 0, d1, -1 * d1))
```

> **Req. lookback ≈ 6d** (minimum for the last day) · use ~11d with buffer.
Regime-conditional 1-day momentum/reversion. Noisy and high turnover (trades the daily change).

## Alpha #10 — score 4/10
*Cross-sectional rank of #9's core.*
```python
d1    = delta(close, 1)
inner = np.where(ts_min(d1, 4) > 0, d1, np.where(ts_max(d1, 4) < 0, d1, -1 * d1))
alpha = rank(inner)
```

> **Req. lookback ≈ 5d** (minimum for the last day) · use ~10d with buffer.
Ranked version of #9 (4d window). Very correlated with #9 — pick one.

## Alpha #11 — score 5/10
*(vwap−close) range over 3d, scaled by volume-change rank.*
```python
vc    = vwap - close
alpha = (rank(ts_max(vc, 3)) + rank(ts_min(vc, 3))) * rank(delta(volume, 3))
```

> **Req. lookback ≈ 4d** (minimum for the last day) · use ~9d with buffer.
Reasonable "where is close vs vwap, weighted by volume acceleration." vwap-proxy dependent.

## Alpha #12 — score 6/10
*If volume rose, fade today's price move.*
```python
alpha = np.sign(delta(volume, 1)) * (-1 * delta(close, 1))
```

> **Req. lookback ≈ 2d** (minimum for the last day) · use ~7d with buffer.
Textbook cheap reversion; well-known to have a small but persistent edge. Turnover moderate-high.

## Alpha #13 — score 6/10
*−rank of covariance(rank close, rank volume).*
```python
alpha = -1 * rank(covariance(rank(close), rank(volume), 5))
```

> **Req. lookback ≈ 5d** (minimum for the last day) · use ~10d with buffer.
Solid price-volume reversion. Note `covariance` is reconstructed as `corr·std·std`; exact up to the
operators' normalization, and monotonic under the outer rank so it barely matters.

## Alpha #14 — score 5/10
*−rank(Δreturns) × correlation(open, volume).*
```python
alpha = (-1 * rank(delta(returns, 3))) * ts_corr_binary(open, volume, 10)
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Combines return-acceleration reversion with the open/volume corr from #6. Moderate; partly redundant
with #6.

## Alpha #15 — score 6/10
*−sum of daily rank-correlations(high, volume).*
```python
alpha = -1 * ts_sum(rank(ts_corr_binary(rank(high), rank(volume), 3)), 3)
```

> **Req. lookback ≈ 5d** (minimum for the last day) · use ~10d with buffer.
Robust price-volume reversion with a smoothing sum → lower turnover than most here. A good pool
candidate.

## Alpha #16 — score 6/10
*−rank(covariance(rank high, rank volume)).*
```python
alpha = -1 * rank(covariance(rank(high), rank(volume), 5))
```

> **Req. lookback ≈ 5d** (minimum for the last day) · use ~10d with buffer.
The `high` analogue of #13; similar quality. Likely correlated with #13/#15.

## Alpha #17 — score 5/10
*Triple-rank: fade recent close rank, its acceleration, and relative volume.*
```python
alpha = (-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1)) \
        * rank(ts_rank(volume / adv(20), 5))
```

> **Req. lookback ≈ 24d** (minimum for the last day) · use ~29d with buffer.
`delta(delta(close,1),1)` is the 2nd difference (price acceleration). Busy but coherent; moderate
turnover.

## Alpha #18 — score 5/10
*−rank of (intraday-range vol + gap + close/open corr).*
```python
co    = close - open
alpha = -1 * rank(ts_std(np.abs(co), 5) + co + ts_corr_binary(close, open, 10))
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Reversion on intraday behaviour. Reasonable; the three summed terms have different scales but the
rank absorbs it.

## Alpha #19 — score 4/10
*Sign of 7d momentum, weighted up by long-horizon return.*
```python
alpha = (-1 * np.sign((close - ts_delay(close, 7)) + delta(close, 7))) \
        * (1 + rank(1 + ts_sum(returns, 250)))
```

> **Req. lookback ≈ 251d** (minimum for the last day) · use ~261d with buffer.
Weak: the sign term is coarse and the 250d weight barely differentiates names. **Needs ≥251d
lookback** in slow mode.

## Alpha #20 — score 5/10
*Fade the overnight gap vs prior high/close/low.*
```python
alpha = (-1 * rank(open - ts_delay(high, 1))) * rank(open - ts_delay(close, 1)) \
        * rank(open - ts_delay(low, 1))
```

> **Req. lookback ≈ 2d** (minimum for the last day) · use ~7d with buffer.
Classic gap-reversion; real but higher turnover (trades every open). Decent diversifier.

## Alpha #21 — score 5/10
*MA-crossover regime, ±1 positions.*
```python
m8 = ts_mean(close, 8); s8 = ts_std(close, 8); m2 = ts_mean(close, 2)
vr = volume / adv(20)
alpha = np.where(m8 + s8 < m2, -1.0,
        np.where(m2 < m8 - s8,  1.0,
        np.where(vr >= 1,       1.0, -1.0)))
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
Bollinger-ish regime switch. I collapsed the paper's `(1<vr)||(vr==1)` to `vr>=1` (avoids fragile
float `==`). Binary ±1 → high turnover; the IR/√TVR tiebreak will hurt.

## Alpha #22 — score 5/10
*−Δ(corr(high, volume)) × rank(close vol).*
```python
alpha = -1 * (delta(ts_corr_binary(high, volume, 5), 5) * rank(ts_std(close, 20)))
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
Change-in-correlation signal scaled by volatility. Moderate; the double time-derivative adds noise.

## Alpha #23 — score 4/10 *(adapted)*
*If above its 20d average high, fade the 2d high move.*
```python
alpha = np.where(ts_mean(high, 20) < high, -1 * delta(high, 2), np.nan)
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
**Adaptation:** the paper's `else 0` is replaced with `np.nan` — in Trexsim a literal `0` becomes a
real (long/short) position after demeaning, which you don't want. Sparse signal (only fires near
20d highs).

## Alpha #24 — score 4/10 *(adapted)*
*Regime switch on the 100d trend of the 100d MA.*
```python
base  = ts_mean(close, 100)
ratio = delta(base, 100) / ts_delay(close, 100)
alpha = np.where(ratio <= 0.05, -1 * (close - ts_min(close, 100)), -1 * delta(close, 3))
```

> **Req. lookback ≈ 200d** (minimum for the last day) · use ~210d with buffer.
**Adaptation:** `(<0.05)||(==0.05)` → `<=0.05`. Slow, needs ~200d lookback; the branch boundary is
brittle. Low turnover at least.

## Alpha #25 — score 5/10
*Reversion weighted by liquidity, vwap, and intraday range.*
```python
alpha = rank((-1 * returns) * adv(20) * vwap * (high - close))
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
Everything gets rank-wrapped so the mixed dollar/price/volume units are OK. vwap-proxy dependent.

## Alpha #26 — score 5/10
*−max over 3d of corr(ts_rank volume, ts_rank high).*
```python
alpha = -1 * ts_max(ts_corr_binary(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
```

> **Req. lookback ≈ 11d** (minimum for the last day) · use ~16d with buffer.
Price-volume reversion on time-series ranks; moderate, fairly diversifying vs the cross-sectional
corr alphas.

## Alpha #27 — score 4/10 *(adapted)*
*Flip sign when smoothed volume/vwap corr is high.*
```python
c     = ts_corr_binary(rank(volume), rank(vwap), 6)
alpha = np.where(rank(ts_sum(c, 2) / 2.0) > 0.5, -1.0, 1.0)
```

> **Req. lookback ≈ 7d** (minimum for the last day) · use ~12d with buffer.
The `>0.5` threshold is **only correct because `rank` returns [0,1]** (my helper). Binary ±1 → high
turnover, and vwap-proxy dependent. Screen it in fast mode first.

## Alpha #28 — score 5/10
*Deviation of mid-price from close, adjusted by adv/low corr; scaled.*
```python
alpha = scale(ts_corr_binary(adv(20), low, 5) + (high + low) / 2.0 - close)
```

> **Req. lookback ≈ 24d** (minimum for the last day) · use ~29d with buffer.
Uses the paper's `scale` (sum|·|=1), **not** `cs_scale`. Mild reversion; fine.

## Alpha #29 — score 2/10 *(fragile)*
*Deeply nested rank/scale/log/product chain + short-return momentum.*
```python
inner = rank(rank(-1 * rank(delta(close - 1, 5))))
mn    = ts_min(inner, 2)
sc    = scale(np.log(ts_sum(mn, 1)))      # log of a tiny scaled positive → numerically delicate
part1 = ts_min(product(rank(rank(sc)), 1), 5)
part2 = ts_rank(ts_delay(-1 * returns, 6), 5)
alpha = part1 + part2
```

> **Req. lookback ≈ 12d** (minimum for the last day) · use ~17d with buffer.
Honestly a mess to trust: `log(scale(...))` on near-zero values is numerically unstable and the
`part1` branch is over-processed. `part2` (short-term reversion) is the only clean bit — consider
trading **just `part2`** instead. Low confidence as written.

## Alpha #30 — score 6/10
*Fade names on a 3-day monotone streak, weighted by volume ratio.*
```python
s = (np.sign(close - ts_delay(close, 1))
     + np.sign(ts_delay(close, 1) - ts_delay(close, 2))
     + np.sign(ts_delay(close, 2) - ts_delay(close, 3)))
alpha = (1.0 - rank(s)) * ts_sum(volume, 5) / ts_sum(volume, 20)
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
Nice, interpretable short-term reversion with a volume-surge tilt. One of the better standalone
candidates in this batch.

## Alpha #31 — score 4/10
*Triple-ranked decay momentum + short reversion + corr sign.*
```python
p1 = rank(rank(rank(decay_linear(-1 * rank(rank(delta(close, 10))), 10))))
p2 = rank(-1 * delta(close, 3))
p3 = np.sign(scale(ts_corr_binary(adv(20), low, 12)))
alpha = p1 + p2 + p3
```

> **Req. lookback ≈ 31d** (minimum for the last day) · use ~36d with buffer.
Three summed pieces on different scales (two ranks in [0,1] plus a sign in {−1,0,1}) → `p3` can
dominate oddly. Muddy; would benefit from z-scoring each part before summing.

## Alpha #32 — score 5/10
*Short MA-reversion + long-horizon vwap/close corr, both scaled.*
```python
alpha = scale(ts_mean(close, 7) - close) \
        + 20 * scale(ts_corr_binary(vwap, ts_delay(close, 5), 230))
```

> **Req. lookback ≈ 235d** (minimum for the last day) · use ~245d with buffer.
Blends fast reversion with a slow lead-lag term. **Needs ~231d lookback**; vwap-proxy dependent. The
`20×` weight is the paper's — tune it.

## Alpha #33 — score 6/10
*Intraday reversion: rank of −(1 − open/close).*
```python
alpha = rank(-1 * (1 - open / close))
```

> **Req. lookback ≈ 1d** (minimum for the last day) · use ~6d with buffer.
Simplifies to ranking the intraday return (close/open). Clean, cheap, dimensionless — a reliable
small-edge reversion alpha and a good baseline.

---

## Quick pool-building notes

- **Best standalone bets in 1–33 (my read):** 3, 6, 12, 13, 15, 16, 30, 33 (cheap, interpretable
  reversion). Start here.
- **Correlation clusters to prune:** {3, 6, 14}, {13, 16, 15}, {9, 10} — keep the highest
  IR/√TVR from each and drop the rest (competition caps pool correlation at 50%).
- **High-turnover watchlist:** 7, 9, 20, 21, 27 — fine for IR but the IR/√TVR tiebreak penalizes
  them; consider `ts_mean_exp(alpha, ...)` to slow them down.
- **vwap-proxy sensitive:** 5, 11, 25, 27, 32 — re-run with a first/last-hour VWAP blend to check
  the proxy isn't carrying the signal.
- **Always screen in fast mode, then confirm in slow mode** with enough lookback (250+ for
  19/24/32). Fast≠slow differences here usually mean insufficient lookback.

---

## Alpha #34 — 6/10
*Low recent-vol + reversion.*
```python
alpha = rank((1 - rank(ts_std(returns, 2) / ts_std(returns, 5))) + (1 - rank(delta(close, 1))))
```

> **Req. lookback ≈ 6d** (minimum for the last day) · use ~11d with buffer.
Clean: buys low short-term-vol names that just dropped. Dependable reversion.

## Alpha #35 — 6/10
*Volume rank × inverse price-position × inverse return rank.*
```python
alpha = (ts_rank(volume, 32) * (1 - ts_rank((close + high) - low, 16))) * (1 - ts_rank(returns, 32))
```

> **Req. lookback ≈ 33d** (minimum for the last day) · use ~38d with buffer.
Uses native `ts_rank` [1,2]; the `1 - ts_rank` terms go negative but it's monotone and demeaned. Solid.

## Alpha #36 — 6/10
*Six-term weighted combo (reversion + momentum + volume corr).*
```python
alpha = (2.21 * rank(ts_corr_binary(close - open, ts_delay(volume, 1), 15))
         + 0.70 * rank(open - close)
         + 0.73 * rank(ts_rank(ts_delay(-1 * returns, 6), 5))
         + rank(np.abs(ts_corr_binary(vwap, adv(20), 6)))
         + 0.60 * rank((ts_mean(close, 200) - open) * (close - open)))
```

> **Req. lookback ≈ 200d** (minimum for the last day) · use ~210d with buffer.
Well-engineered multi-signal blend. Needs ~200d lookback + vwap proxy. Good pool candidate.

## Alpha #37 — 6/10
*Lagged gap correlation + gap reversion.*
```python
alpha = rank(ts_corr_binary(ts_delay(open - close, 1), close, 200)) + rank(open - close)
```

> **Req. lookback ≈ 201d** (minimum for the last day) · use ~211d with buffer.
Nice and interpretable, but the 200d correlation makes it slow — needs 200+ lookback.

## Alpha #38 — 5/10
*Fade high recent close-rank, scaled by close/open.*
```python
alpha = (-1 * rank(ts_rank(close, 10))) * rank(close / open)
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Moderate reversion; overlaps with other close-rank alphas.

## Alpha #39 — 5/10
*7d reversion damped by volume decay, weighted by 250d return.*
```python
alpha = (-1 * rank(delta(close, 7) * (1 - rank(decay_linear(volume / adv(20), 9))))) \
        * (1 + rank(ts_sum(returns, 250)))
```

> **Req. lookback ≈ 251d** (minimum for the last day) · use ~261d with buffer.
Reasonable but the 250d weight barely separates names. Needs 250+ lookback.

## Alpha #40 — 6/10
*Fade high-vol names, tilt by high/volume corr.*
```python
alpha = (-1 * rank(ts_std(high, 10))) * ts_corr_binary(high, volume, 10)
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Clean volatility-reversion × price-volume. Decent, cheap.

## Alpha #41 — 4/10
*Geometric mid-price minus vwap.*
```python
alpha = np.sqrt(high * low) - vwap
```

> **Req. lookback ≈ 1d** (minimum for the last day) · use ~6d with buffer.
**Not dimensionless** (units of price) → exposed to corporate-adjustment fast/slow gaps, and pure
vwap-proxy. Weak/risky as written; consider dividing by `close`.

## Alpha #42 — 5/10 *(delay-0)*
*(vwap−close)/(vwap+close), ranked.*
```python
alpha = rank(vwap - close) / rank(vwap + close)
```

> **Req. lookback ≈ 1d** (minimum for the last day) · use ~6d with buffer.
Designed to trade at the close; in Trexsim it becomes delay-1, so expect different behaviour. vwap
proxy dependent.

## Alpha #43 — 6/10
*Relative-volume rank × 7d price reversion.*
```python
alpha = ts_rank(volume / adv(20), 20) * ts_rank(-1 * delta(close, 7), 8)
```

> **Req. lookback ≈ 39d** (minimum for the last day) · use ~44d with buffer.
Interpretable volume-confirmed reversion. Good diversifier.

## Alpha #44 — 6/10
*−correlation(high, rank volume).*
```python
alpha = -1 * ts_corr_binary(high, rank(volume), 5)
```

> **Req. lookback ≈ 5d** (minimum for the last day) · use ~10d with buffer.
Simple, robust price-volume reversion. Likely correlated with #40/#15 — prune.

## Alpha #45 — 5/10
*Lagged MA reversion × two correlations.*
```python
alpha = -1 * (rank(ts_mean(ts_delay(close, 5), 20)) * ts_corr_binary(close, volume, 2)
              * rank(ts_corr_binary(ts_sum(close, 5), ts_sum(close, 20), 2)))
```

> **Req. lookback ≈ 25d** (minimum for the last day) · use ~30d with buffer.
Busy; the 2d correlations are noisy. Moderate.

## Alpha #46 — 5/10
*Trend-curvature regime, ±1 or 1d reversion.*
```python
curv = ((ts_delay(close, 20) - ts_delay(close, 10)) / 10) - ((ts_delay(close, 10) - close) / 10)
alpha = np.where(curv > 0.25, -1.0, np.where(curv < 0, 1.0, -1.0 * (close - ts_delay(close, 1))))
```

> **Req. lookback ≈ 21d** (minimum for the last day) · use ~26d with buffer.
Second-derivative-of-price regime switch. Binary branches → higher turnover.

## Alpha #47 — 5/10
*Liquidity-weighted reversion minus vwap change.*
```python
alpha = ((rank(1 / close) * volume / adv(20)) * (high * rank(high - close) / ts_mean(high, 5))) \
        - rank(vwap - ts_delay(vwap, 5))
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
The two summed parts are on very different scales — consider z-scoring each. vwap proxy.

## Alpha #48 — 6/10 *(delay-0, industry)*
*Serial-correlation reversion, industry-neutral, vol-normalized.*
```python
num   = ts_corr_binary(delta(close, 1), delta(ts_delay(close, 1), 1), 250) * delta(close, 1) / close
alpha = cs_indneut(num, subindustry) / ts_sum((delta(close, 1) / ts_delay(close, 1)) ** 2, 250)
```

> **Req. lookback ≈ 252d** (minimum for the last day) · use ~262d with buffer.
A well-known, genuinely good reversion alpha — but **delay-0**, needs `subindustry`, and **250+d
lookback**. Heavy but worth including.

## Alpha #49 — 5/10
*Curvature threshold (sibling of #46/#51).*
```python
curv = ((ts_delay(close, 20) - ts_delay(close, 10)) / 10) - ((ts_delay(close, 10) - close) / 10)
alpha = np.where(curv < -0.1, 1.0, -1.0 * (close - ts_delay(close, 1)))
```

> **Req. lookback ≈ 21d** (minimum for the last day) · use ~26d with buffer.
Lower turnover than #46. Keep only one of {46, 49, 51}.

## Alpha #50 — 6/10
*−max of ranked volume/vwap correlation.*
```python
alpha = -1 * ts_max(rank(ts_corr_binary(rank(volume), rank(vwap), 5)), 5)
```

> **Req. lookback ≈ 9d** (minimum for the last day) · use ~14d with buffer.
Clean price-volume reversion. vwap proxy but rank-wrapped so mild exposure.

## Alpha #51 — 5/10
*Curvature threshold sibling.*
```python
curv = ((ts_delay(close, 20) - ts_delay(close, 10)) / 10) - ((ts_delay(close, 10) - close) / 10)
alpha = np.where(curv < -0.05, 1.0, -1.0 * (close - ts_delay(close, 1)))
```

> **Req. lookback ≈ 21d** (minimum for the last day) · use ~26d with buffer.
Same family as #46/#49; redundant with them.

## Alpha #52 — 5/10
*Low-breakout reversal + long-horizon momentum + volume.*
```python
alpha = ((-1 * ts_min(low, 5) + ts_delay(ts_min(low, 5), 5))
         * rank((ts_sum(returns, 240) - ts_sum(returns, 20)) / 220)) * ts_rank(volume, 5)
```

> **Req. lookback ≈ 241d** (minimum for the last day) · use ~251d with buffer.
Combines short reversal with 12-month-ex-1-month momentum. Needs 240+d lookback.

## Alpha #53 — 6/10 *(delay-0)*
*Reversion of intraday close-position.*
```python
alpha = -1 * delta(((close - low) - (high - close)) / (close - low), 9)
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Clean, dimensionless intraday-position reversion. Good — but delay-0 (trades close).

## Alpha #54 — 6/10 *(delay-0)*
*Intraday position via power ratio.*
```python
alpha = (-1 * ((low - close) * (open ** 5))) / ((low - high) * (close ** 5))
```

> **Req. lookback ≈ 1d** (minimum for the last day) · use ~6d with buffer.
The `open^5/close^5` isn't dimensionless → some adjustment risk, but it largely cancels. Decent
delay-0 reversion.

## Alpha #55 — 6/10
*Stochastic-%K reversion vs volume.*
```python
k     = (close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low, 12))
alpha = -1 * ts_corr_binary(rank(k), rank(volume), 6)
```

> **Req. lookback ≈ 17d** (minimum for the last day) · use ~22d with buffer.
Nice: fades names where %K and volume co-move. Good candidate.

## Alpha #56 — 4/10 *(needs mktcap)*
*Short/long return ratio × size-weighted return.*
```python
alpha = -1 * (rank(ts_sum(returns, 10) / ts_sum(ts_sum(returns, 2), 3)) * rank(returns * mktcap))
```

> **Req. lookback ≈ 11d** (minimum for the last day) · use ~16d with buffer.
The only market-cap alpha. Weak signal and size-tilted; treat as a diversifier.

## Alpha #57 — 5/10
*(close−vwap) reversion damped by recent-high timing.*
```python
alpha = -1 * ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2))
```

> **Req. lookback ≈ 31d** (minimum for the last day) · use ~36d with buffer.
Reasonable reversion; vwap proxy + the 30d argmax adds noise.

## Alpha #58 — 5/10 *(industry)*
*Industry-neutral vwap/volume corr, decayed & ranked.*
```python
alpha = -1 * ts_rank(decay_linear(ts_corr_binary(cs_indneut(vwap, sector), volume, 3), 7), 5)
```

> **Req. lookback ≈ 13d** (minimum for the last day) · use ~18d with buffer.
Template alpha. Needs `sector` + vwap proxy; fitted constants → validate.

## Alpha #59 — 5/10 *(industry)*
*Same as #58, industry level.*
```python
# vwap*0.728 + vwap*(1-0.728) == vwap  (weights collapse)
alpha = -1 * ts_rank(decay_linear(ts_corr_binary(cs_indneut(vwap, industry), volume, 4), 16), 8)
```

> **Req. lookback ≈ 26d** (minimum for the last day) · use ~31d with buffer.
Redundant blend simplified. Very correlated with #58.

## Alpha #60 — 5/10
*Scaled intraday-position×volume minus scaled recent-high timing.*
```python
x     = ((close - low) - (high - close)) / (high - low) * volume
alpha = -1 * (2 * scale(rank(x)) - scale(rank(ts_argmax(close, 10))))
```

> **Req. lookback ≈ 10d** (minimum for the last day) · use ~15d with buffer.
Uses paper `scale`. Moderate; the two scaled ranks are comparable in size, which is the point.

## Alpha #61 — 5/10
*vwap dip vs vwap/adv correlation.*
```python
alpha = (rank(vwap - ts_min(vwap, 16)) < rank(ts_corr_binary(vwap, adv(180), 17))).astype(float)
```

> **Req. lookback ≈ 196d** (minimum for the last day) · use ~206d with buffer.
Binary. Needs adv180 (~200d). vwap proxy.

## Alpha #62 — 4/10
*Nested boolean vwap/adv vs open-structure.*
```python
inner = ((rank(open) + rank(open)) < (rank((high + low) / 2) + rank(high))).astype(float)
alpha = (rank(ts_corr_binary(vwap, ts_sum(adv(20), 22), 9)) < rank(inner)) * -1
```

> **Req. lookback ≈ 49d** (minimum for the last day) · use ~54d with buffer.
Over-nested; the inner boolean is coarse. Muddy.

## Alpha #63 — 5/10 *(industry)*
*Industry-neutral close momentum minus price/adv corr.*
```python
blend = vwap * 0.318108 + open * (1 - 0.318108)
alpha = (rank(decay_linear(delta(cs_indneut(close, industry), 2), 8))
         - rank(decay_linear(ts_corr_binary(blend, ts_sum(adv(180), 37), 13), 12))) * -1
```

> **Req. lookback ≈ 239d** (minimum for the last day) · use ~249d with buffer.
Template; needs adv180 + industry. Fitted constants.

## Alpha #64 — 5/10
*Blended-price/adv corr vs mid/vwap change.*
```python
b1 = open * 0.178404 + low * (1 - 0.178404)
b2 = ((high + low) / 2) * 0.178404 + vwap * (1 - 0.178404)
alpha = (rank(ts_corr_binary(ts_sum(b1, 12), ts_sum(adv(120), 12), 16)) < rank(delta(b2, 3))) * -1
```

> **Req. lookback ≈ 146d** (minimum for the last day) · use ~156d with buffer.
Binary; adv120. Moderate.

## Alpha #65 — 5/10
*Open/vwap-blend vs adv corr, vs open dip.*
```python
b     = open * 0.00817205 + vwap * (1 - 0.00817205)   # ≈ open
alpha = (rank(ts_corr_binary(b, ts_sum(adv(60), 8), 6)) < rank(open - ts_min(open, 13))) * -1
```

> **Req. lookback ≈ 72d** (minimum for the last day) · use ~77d with buffer.
The blend is ~all-open; effectively an open-based binary. Moderate.

## Alpha #66 — 4/10
*Decayed vwap change + odd low/vwap ratio.*
```python
num   = (low - vwap) / (open - (high + low) / 2)     # denominator can blow up near 0
alpha = (rank(decay_linear(delta(vwap, 3), 7)) + ts_rank(decay_linear(num, 11), 6)) * -1
```

> **Req. lookback ≈ 16d** (minimum for the last day) · use ~21d with buffer.
The `(open − mid)` denominator is often near zero → unstable. Fragile.

## Alpha #67 — 5/10 *(industry)*
*High dip ^ industry-neutral vwap/adv corr.*
```python
alpha = (rank(high - ts_min(high, 2))
         ** rank(ts_corr_binary(cs_indneut(vwap, sector), cs_indneut(adv(20), subindustry), 6))) * -1
```

> **Req. lookback ≈ 25d** (minimum for the last day) · use ~30d with buffer.
Two-level neutralization; base in [0,1] so power is safe. Complex.

## Alpha #68 — 5/10
*High/adv corr rank vs close/low-blend change.*
```python
b     = close * 0.518371 + low * (1 - 0.518371)
alpha = (ts_rank(ts_corr_binary(rank(high), rank(adv(15)), 8), 13) < rank(delta(b, 1))) * -1
```

> **Req. lookback ≈ 34d** (minimum for the last day) · use ~39d with buffer.
Binary; reasonable price-volume structure. Moderate.

## Alpha #69 — 4/10 *(industry)*
*Industry-neutral vwap momentum ^ price/adv corr.*
```python
b     = close * 0.490655 + vwap * (1 - 0.490655)
alpha = (rank(ts_max(delta(cs_indneut(vwap, industry), 2), 4))
         ** ts_rank(ts_corr_binary(b, adv(20), 4), 9)) * -1
```

> **Req. lookback ≈ 31d** (minimum for the last day) · use ~36d with buffer.
Fitted + fragile power base near 0. Complex.

## Alpha #70 — 5/10 *(industry)*
*vwap change ^ industry-neutral close/adv corr.*
```python
alpha = (rank(delta(vwap, 1))
         ** ts_rank(ts_corr_binary(cs_indneut(close, industry), adv(50), 17), 17)) * -1
```

> **Req. lookback ≈ 82d** (minimum for the last day) · use ~87d with buffer.
Template; adv50 + industry. Moderate.

## Alpha #71 — 6/10
*Max of two legs: close/adv corr decay, and mid/vwap squared.*
```python
leg1  = ts_rank(decay_linear(ts_corr_binary(ts_rank(close, 3), ts_rank(adv(180), 12), 18), 4), 15)
leg2  = ts_rank(decay_linear(rank((low + open) - (vwap + vwap)) ** 2, 16), 4)
alpha = np.maximum(leg1, leg2)
```

> **Req. lookback ≈ 225d** (minimum for the last day) · use ~235d with buffer.
The `max` of two views is robust; a known solid alpha. Needs adv180.

## Alpha #72 — 6/10
*Ratio of two decayed correlations (mid/adv vs vwap/vol).*
```python
alpha = (rank(decay_linear(ts_corr_binary((high + low) / 2, adv(40), 8), 10))
         / rank(decay_linear(ts_corr_binary(ts_rank(vwap, 3), ts_rank(volume, 18), 6), 2)))
```

> **Req. lookback ≈ 56d** (minimum for the last day) · use ~61d with buffer.
Interpretable liquidity-vs-activity ratio. Decent.

## Alpha #73 — 4/10
*Max(vwap-change decay, blended-price momentum).*
```python
b     = open * 0.147155 + low * (1 - 0.147155)
alpha = np.maximum(rank(decay_linear(delta(vwap, 4), 2)),
                   ts_rank(decay_linear((delta(b, 2) / b) * -1, 3), 16)) * -1
```

> **Req. lookback ≈ 20d** (minimum for the last day) · use ~25d with buffer.
OK but the `delta(b,2)/b` term is noisy. Middling.

## Alpha #74 — 5/10
*close/adv corr vs blended-price/volume corr.*
```python
b     = high * 0.0261661 + vwap * (1 - 0.0261661)     # ≈ vwap
alpha = (rank(ts_corr_binary(close, ts_sum(adv(30), 37), 15))
         < rank(ts_corr_binary(rank(b), rank(volume), 11))) * -1
```

> **Req. lookback ≈ 80d** (minimum for the last day) · use ~85d with buffer.
Binary; needs ~37d adv-sum lookback. Moderate.

## Alpha #75 — 5/10
*vwap/vol corr vs low/adv corr.*
```python
alpha = (rank(ts_corr_binary(vwap, volume, 4)) < rank(ts_corr_binary(rank(low), rank(adv(50)), 12))).astype(float)
```

> **Req. lookback ≈ 61d** (minimum for the last day) · use ~66d with buffer.
Clean binary price-volume contrast. Moderate.

## Alpha #76 — 4/10 *(industry)*
*Max(vwap-change decay, deep nested low/adv corr).*
```python
alpha = np.maximum(
    rank(decay_linear(delta(vwap, 1), 11)),
    ts_rank(decay_linear(ts_rank(ts_corr_binary(cs_indneut(low, sector), adv(81), 8), 19), 17), 19)
) * -1
```

> **Req. lookback ≈ 140d** (minimum for the last day) · use ~150d with buffer.
Very deep nesting + fitted constants → overfit risk. Lower confidence.

## Alpha #77 — 6/10
*Min(mid−vwap decay, mid/adv corr decay).*
```python
alpha = np.minimum(
    rank(decay_linear(((high + low) / 2 + high) - (vwap + high), 20)),   # == mid - vwap
    rank(decay_linear(ts_corr_binary((high + low) / 2, adv(40), 3), 5)))
```

> **Req. lookback ≈ 46d** (minimum for the last day) · use ~51d with buffer.
The `min` of a reversion view and a liquidity view is robust. Decent.

## Alpha #78 — 6/10
*Blended-price/adv corr ^ vwap/vol corr.*
```python
b     = low * 0.352233 + vwap * (1 - 0.352233)
alpha = rank(ts_corr_binary(ts_sum(b, 19), ts_sum(adv(40), 19), 6)) \
        ** rank(ts_corr_binary(rank(vwap), rank(volume), 5))
```

> **Req. lookback ≈ 63d** (minimum for the last day) · use ~68d with buffer.
A well-regarded price-volume alpha. Base in [0,1] so power is safe. Good.

## Alpha #79 — 5/10 *(industry)*
*Industry-neutral price change vs vwap/adv corr.*
```python
b     = close * 0.60733 + open * (1 - 0.60733)
alpha = (rank(delta(cs_indneut(b, sector), 1))
         < rank(ts_corr_binary(ts_rank(vwap, 3), ts_rank(adv(150), 9), 14))).astype(float)
```

> **Req. lookback ≈ 171d** (minimum for the last day) · use ~181d with buffer.
Binary; needs adv150 + sector. Moderate.

## Alpha #80 — 4/10 *(industry)*
*sign(industry-neutral momentum) ^ high/adv corr.*
```python
b     = open * 0.868128 + high * (1 - 0.868128)
alpha = (rank(np.sign(delta(cs_indneut(b, industry), 4)))
         ** ts_rank(ts_corr_binary(high, adv(10), 5), 5)) * -1
```

> **Req. lookback ≈ 18d** (minimum for the last day) · use ~23d with buffer.
Sign inside a power is coarse. Fragile.

## Alpha #81 — 3/10 *(fragile)*
*Log-product of ranked vwap/adv corr vs vwap/vol corr.*
```python
inner = product(rank(rank(ts_corr_binary(vwap, ts_sum(adv(10), 49), 8)) ** 4), 14)
alpha = (rank(np.log(inner)) < rank(ts_corr_binary(rank(vwap), rank(volume), 5))) * -1
```

> **Req. lookback ≈ 78d** (minimum for the last day) · use ~83d with buffer.
Like #29: `log(product(...))` on tiny values is numerically unstable. Low confidence.

## Alpha #82 — 5/10 *(industry)*
*Min(open-change decay, industry-neutral volume/open corr).*
```python
alpha = np.minimum(
    rank(decay_linear(delta(open, 1), 14)),
    ts_rank(decay_linear(ts_corr_binary(cs_indneut(volume, sector), open, 17), 6), 13)) * -1
```

> **Req. lookback ≈ 34d** (minimum for the last day) · use ~39d with buffer.
Blend collapses to `open`. Template; moderate.

## Alpha #83 — 4/10
*Range/MA ratio, volume rank, vwap−close denominator.*
```python
r     = (high - low) / ts_mean(close, 5)
alpha = (rank(ts_delay(r, 2)) * rank(rank(volume))) / (r / (vwap - close))
```

> **Req. lookback ≈ 7d** (minimum for the last day) · use ~12d with buffer.
The `(vwap − close)` in the denominator crosses zero → unstable. Fragile.

## Alpha #84 — 5/10
*signedpower(vwap-vs-recent-max rank, close change).*
```python
alpha = signedpower(ts_rank(vwap - ts_max(vwap, 15), 20), delta(close, 4))
```

> **Req. lookback ≈ 34d** (minimum for the last day) · use ~39d with buffer.
Matrix exponent (`delta(close,4)`); base is positive `ts_rank` so it's well-defined. Odd but valid.
vwap proxy.

## Alpha #85 — 6/10
*High/close-blend/adv corr ^ mid/volume corr.*
```python
b     = high * 0.876703 + close * (1 - 0.876703)
alpha = rank(ts_corr_binary(b, adv(30), 9)) \
        ** rank(ts_corr_binary(ts_rank((high + low) / 2, 3), ts_rank(volume, 10), 7))
```

> **Req. lookback ≈ 38d** (minimum for the last day) · use ~43d with buffer.
Solid price-volume structure, no industry data needed. Good candidate.

## Alpha #86 — 5/10
*close/adv corr rank vs (close−vwap).*
```python
alpha = (ts_rank(ts_corr_binary(close, ts_sum(adv(20), 14), 6), 20)
         < rank((open + close) - (vwap + open))) * -1     # rhs == close - vwap
```

> **Req. lookback ≈ 57d** (minimum for the last day) · use ~62d with buffer.
Binary; the rhs simplifies to `close − vwap`. Moderate. vwap proxy.

## Alpha #87 — 5/10 *(industry)*
*Max(close/vwap-blend change decay, |industry adv/close corr|).*
```python
b     = close * 0.369701 + vwap * (1 - 0.369701)
alpha = np.maximum(
    rank(decay_linear(delta(b, 1), 2)),
    ts_rank(decay_linear(np.abs(ts_corr_binary(cs_indneut(adv(81), industry), close, 13)), 4), 14)) * -1
```

> **Req. lookback ≈ 109d** (minimum for the last day) · use ~119d with buffer.
Template; adv81 + industry. Moderate.

## Alpha #88 — 6/10
*Min(rank-structure decay, close/adv corr decay).*
```python
leg1  = rank(decay_linear((rank(open) + rank(low)) - (rank(high) + rank(close)), 8))
leg2  = ts_rank(decay_linear(ts_corr_binary(ts_rank(close, 8), ts_rank(adv(60), 20), 8), 6), 2)
alpha = np.minimum(leg1, leg2)
```

> **Req. lookback ≈ 92d** (minimum for the last day) · use ~97d with buffer.
No industry data; robust `min` of two clean views. Good.

## Alpha #89 — 4/10 *(industry)*
*Low/adv corr decay minus industry-neutral vwap change decay.*
```python
alpha = (ts_rank(decay_linear(ts_corr_binary(low, adv(10), 6), 5), 3)
         - ts_rank(decay_linear(delta(cs_indneut(vwap, industry), 3), 10), 15))
```

> **Req. lookback ≈ 27d** (minimum for the last day) · use ~32d with buffer.
Blend collapses to `low`. Complex difference of two ts_ranks; middling.

## Alpha #90 — 5/10 *(industry)*
*Close-vs-recent-max ^ industry-neutral adv/low corr.*
```python
alpha = (rank(close - ts_max(close, 4))
         ** ts_rank(ts_corr_binary(cs_indneut(adv(40), subindustry), low, 5), 3)) * -1
```

> **Req. lookback ≈ 46d** (minimum for the last day) · use ~51d with buffer.
Template; subindustry. Moderate.

## Alpha #91 — 4/10 *(industry)*
*Double-decayed industry close/volume corr minus vwap/adv corr.*
```python
alpha = (ts_rank(decay_linear(decay_linear(ts_corr_binary(cs_indneut(close, industry), volume, 9), 16), 3), 4)
         - rank(decay_linear(ts_corr_binary(vwap, adv(30), 4), 2))) * -1
```

> **Req. lookback ≈ 34d** (minimum for the last day) · use ~39d with buffer.
Double decay + industry → heavily smoothed and overfit-prone. Lower confidence.

## Alpha #92 — 6/10
*Min(intraday-position boolean decay, low/adv corr decay).*
```python
cond  = (((high + low) / 2 + close) < (low + open)).astype(float)
alpha = np.minimum(
    ts_rank(decay_linear(cond, 14), 18),
    ts_rank(decay_linear(ts_corr_binary(rank(low), rank(adv(30)), 7), 6), 6))
```

> **Req. lookback ≈ 46d** (minimum for the last day) · use ~51d with buffer.
No industry data; the boolean captures a real intraday pattern. A respected alpha. Decent.

## Alpha #93 — 4/10 *(industry)*
*Industry vwap/adv corr decay / close-blend change decay.*
```python
b     = close * 0.524434 + vwap * (1 - 0.524434)
alpha = (ts_rank(decay_linear(ts_corr_binary(cs_indneut(vwap, industry), adv(81), 17), 19), 7)
         / rank(decay_linear(delta(b, 2), 16)))
```

> **Req. lookback ≈ 121d** (minimum for the last day) · use ~131d with buffer.
Ratio can be unstable when the denominator rank is near 0. Complex.

## Alpha #94 — 5/10
*vwap dip ^ vwap/adv corr.*
```python
alpha = (rank(vwap - ts_min(vwap, 11))
         ** ts_rank(ts_corr_binary(ts_rank(vwap, 19), ts_rank(adv(60), 4), 18), 2)) * -1
```

> **Req. lookback ≈ 81d** (minimum for the last day) · use ~86d with buffer.
No industry data; vwap proxy. Moderate.

## Alpha #95 — 6/10
*Open dip vs (mid/adv corr)^5 rank.*
```python
inner = rank(ts_corr_binary(ts_sum((high + low) / 2, 19), ts_sum(adv(40), 19), 12)) ** 5
alpha = (rank(open - ts_min(open, 12)) < ts_rank(inner, 11)).astype(float)
```

> **Req. lookback ≈ 79d** (minimum for the last day) · use ~84d with buffer.
The `^5` sharpens the corr signal; clean binary. Decent.

## Alpha #96 — 5/10
*Max(vwap/vol corr decay, argmax of close/adv corr decay).*
```python
leg1  = ts_rank(decay_linear(ts_corr_binary(rank(vwap), rank(volume), 3), 4), 8)
leg2  = ts_rank(decay_linear(ts_argmax(ts_corr_binary(ts_rank(close, 7), ts_rank(adv(60), 4), 3), 12), 14), 13)
alpha = np.maximum(leg1, leg2) * -1
```

> **Req. lookback ≈ 101d** (minimum for the last day) · use ~111d with buffer.
Robust `max`, no industry data, but deep. Moderate.

## Alpha #97 — 4/10 *(industry)*
*Industry-neutral low/vwap change decay minus nested low/adv corr.*
```python
b     = low * 0.721001 + vwap * (1 - 0.721001)
alpha = (rank(decay_linear(delta(cs_indneut(b, industry), 3), 20))
         - ts_rank(decay_linear(ts_rank(ts_corr_binary(ts_rank(low, 7), ts_rank(adv(60), 17), 4), 18), 15), 6)) * -1
```

> **Req. lookback ≈ 115d** (minimum for the last day) · use ~125d with buffer.
Among the most nested — high overfit risk. Lower confidence.

## Alpha #98 — 5/10
*vwap/adv corr decay minus open/adv argmin decay.*
```python
alpha = (rank(decay_linear(ts_corr_binary(vwap, ts_sum(adv(5), 26), 4), 7))
         - rank(decay_linear(ts_rank(ts_argmin(ts_corr_binary(rank(open), rank(adv(15)), 20), 8), 6), 8)))
```

> **Req. lookback ≈ 53d** (minimum for the last day) · use ~58d with buffer.
No industry data. Difference of a liquidity view and a timing view. Moderate.

## Alpha #99 — 6/10
*mid/adv corr vs low/volume corr.*
```python
alpha = (rank(ts_corr_binary(ts_sum((high + low) / 2, 19), ts_sum(adv(60), 19), 8))
         < rank(ts_corr_binary(low, volume, 6))) * -1
```

> **Req. lookback ≈ 85d** (minimum for the last day) · use ~90d with buffer.
Clean binary price-volume contrast, no industry data. Decent.

## Alpha #100 — 6/10 *(industry)*
*Industry-neutral intraday-position reversion, liquidity-scaled.*
```python
x     = ((close - low) - (high - close)) / (high - low) * volume
p1    = 1.5 * scale(cs_indneut(rank(x), subindustry))
p2    = scale(cs_indneut(ts_corr_binary(close, rank(adv(20)), 5) - rank(ts_argmin(close, 30)), subindustry))
alpha = -1 * ((p1 - p2) * (volume / adv(20)))
```

> **Req. lookback ≈ 30d** (minimum for the last day) · use ~35d with buffer.
The paper double-neutralizes by subindustry (idempotent), so I apply it once. A strong, well-known
reversion alpha — needs `subindustry`. Good.

## Alpha #101 — 7/10
*Intraday momentum: body / range.*
```python
alpha = (close - open) / ((high - low) + 0.001)
```

> **Req. lookback ≈ 1d** (minimum for the last day) · use ~6d with buffer.
The paper's showcase delay-1 momentum. Simple, dimensionless, cheap, robust — the best plain baseline
in the whole set.

---

## Pool-building notes (34–101)

- **Best standalone bets:** 34, 35, 40, 43, 44, 48, 53, 55, 71, 72, 77, 78, 85, 88, 92, 95, 99, 100, 101.
  Start here — they're either clean price-volume/reversion or the robust `max`/`min` template alphas.
- **Skip or fix first:** 41 (not dimensionless), 66/83 (blow-up denominators), 81 (log-product
  instability), 76/91/97 (deepest nesting → overfit).
- **Redundancy clusters (keep one each):** {46, 49, 51} curvature; {58, 59} industry vwap corr;
  {40, 44} vol-reversion; {13, 16, 44} price-volume covariance family (with the 1–33 batch).
- **Industry data needed:** 48, 58, 59, 63, 67, 69, 70, 76, 79, 80, 82, 87, 89, 90, 91, 93, 97, 100.
  Use `sector` / `industry` / `subindustry` as the paper specifies.
- **Delay-0 (trade differently in Trexsim):** 42, 48, 53, 54.
- **Long lookback (250+ in slow mode):** 36 (200), 37 (200), 39/48/52 (240–250), plus every
  adv120/adv150/adv180 alpha (~200). Give generous lookback or fast≠slow will bite.
- **Fitted decimal constants** in 58–99 are overfit flags — if an alpha only works at exactly the
  paper's window, it won't survive out-of-sample scoring. Round them and re-test.
