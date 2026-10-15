'use strict';
// Typed formula grammar for the evolutionary search.
// Every leaf is a unit-free "primitive"; composition happens only through ranks/z-scores,
// so formulas never mix units. Trees render to a complete TrexSim Python buffer.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const WINDOWS = [3, 5, 10, 22, 66, 126, 252];
const SHORT_WINDOWS = [3, 5, 10, 22, 66];
const EPS = '1e-6';

function rng(seed) { // mulberry32
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const pick = (r, list) => list[Math.floor(r() * list.length)];

// ---------------------------------------------------------------- primitives
function daily(name, expr, family, positive = false) { return { name, expr, family, kind: 'daily', positive, lookback: 1 }; }

function catalog(root) {
  const index = fs.readFileSync(path.join(root, 'data-map/_INDEX.md'), 'utf8');
  const dist = JSON.parse(fs.readFileSync(path.join(root, 'data-distribution.json'), 'utf8')).items;
  const coverage = Object.fromEntries(dist.map(d => [d.varname, Number(d.coverage) || 0]));
  const rows = [];
  let cluster = null;
  for (const line of index.split('\n')) {
    const h = line.match(/^## (.+?)\s+\((\d+)\)/);
    if (h) { cluster = h[1]; continue; }
    const m = line.match(/^\| `([a-z0-9_]+)`[^|]*\|[^|]*\|\s*([a-z-]+)\s*\|\s*([a-z]+)\s*\|/);
    if (m && cluster) rows.push({ name: m[1], cluster, dim: m[2], freq: m[3], coverage: coverage[m[1]] || 0 });
  }
  return rows;
}

function primitives(root) {
  const P = [];
  // Price / volume (daily, unit-free)
  P.push(daily('ret1', 'ret1', 'pv_return'), daily('ret5', 'ret5', 'pv_return'), daily('ret10', 'ret10', 'pv_return'), daily('ret20', 'ret20', 'pv_return'));
  P.push(daily('open_close', `_div(close - open, open)`, 'pv_return'));
  P.push({ ...daily('gap', `_div(open - ts_delay(close, 1), ts_delay(close, 1))`, 'pv_return'), lookback: 2 });
  P.push(daily('range', `_div(high - low, close)`, 'pv_vol'));
  P.push(daily('close_loc', `_div(close - low, high - low + ${EPS}) - 0.5`, 'pv_shape'));
  P.push(daily('volume', 'volume', 'pv_volume', true));
  P.push(daily('dollar_volume', 'volume * close', 'pv_volume', true));
  P.push(daily('log_mktcap', 'np.log(np.maximum(mktcap, 1e-3))', 'pv_size'));
  // Intraday (daily)
  const H = ['first', 'last'];
  for (const h of H) {
    P.push(daily(`ret_${h}`, `return_${h}_hour`, 'id_return'));
    P.push(daily(`ir_${h}`, `information_ratio_${h}_hour`, 'id_shape'));
    P.push(daily(`std_ret_${h}`, `std_dev_return_${h}_hour`, 'id_vol', true));
    for (const k of ['close', 'return', 'volume']) P.push(daily(`skew_${k}_${h}`, `skew_${k}_${h}_hour`, 'id_shape'));
    P.push(daily(`vol_${h}`, `volume_${h}_hour`, 'id_volume', true));
    P.push(daily(`trades_${h}`, `number_of_trades_${h}_hour`, 'id_volume', true));
    P.push(daily(`trade_size_${h}`, `_div(volume_${h}_hour, number_of_trades_${h}_hour)`, 'id_volume', true));
    P.push(daily(`range_${h}`, `_div(high_price_${h}_hour - low_price_${h}_hour, close)`, 'id_vol', true));
    P.push(daily(`loc_${h}`, `_div(close_price_${h}_hour - low_price_${h}_hour, high_price_${h}_hour - low_price_${h}_hour + ${EPS}) - 0.5`, 'id_shape'));
    P.push(daily(`vwap_dev_${h}`, `_div(close_price_${h}_hour - vwap_${h}_hour, vwap_${h}_hour)`, 'id_pressure'));
    P.push(daily(`std_close_${h}`, `_div(std_close_${h}_hour, close)`, 'id_vol', true));
  }
  P.push(daily('vwap_drift', `_div(vwap_last_hour - vwap_first_hour, vwap_first_hour)`, 'id_pressure'));
  P.push(daily('close_vs_vwap_last', `_div(close - vwap_last_hour, vwap_last_hour)`, 'id_pressure'));
  P.push(daily('vol_share_last', `_div(volume_last_hour, volume_first_hour + volume_last_hour)`, 'id_volume'));
  P.push(daily('trades_share_last', `_div(number_of_trades_last_hour, number_of_trades_first_hour + number_of_trades_last_hour)`, 'id_volume'));
  P.push(daily('ret_last_minus_first', 'return_last_hour - return_first_hour', 'id_return'));
  P.push(daily('mid_session', `_div(open_price_last_hour - close_price_first_hour, close_price_first_hour)`, 'id_return'));
  P.push(daily('earn_proximity', `-trading_days_until_next_earnings_announcement`, 'season_earnings'));

  // Fundamentals (slow), from the catalog: ratios used raw; dollar levels scaled by size.
  const rows = catalog(root).filter(r => r.cluster.startsWith('Fundamental') && r.dim === 'cross-sec' && r.coverage >= 1500);
  const ratioLike = /ratio|pct|margin|yield|growth|return_on|roe|roa|_to_|turnover|coverage|times_interest|normalized/;
  const perShare = /per_share|_eps|eps_|^eps$|per_diluted_share/;
  const shareCount = /shares/; // share COUNTS: only their growth (net issuance) is meaningful
  for (const r of rows) {
    const fam = 'fund_' + r.cluster.split('—')[1].trim().toLowerCase().replace(/\s+/g, '_');
    let expr;
    if (shareCount.test(r.name)) {
      P.push({ name: `${r.name}_issuance`, expr: `(_div(${r.name}, ts_delay(${r.name}, 252)) - 1.0)`, family: fam, kind: 'slow', positive: false, lookback: 253 });
      continue;
    }
    if (perShare.test(r.name)) expr = `_div(${r.name}, close)`;
    else if (ratioLike.test(r.name)) expr = r.name;
    else if (r.name === 'mktcap' || r.name === 'total_assets') continue;
    else expr = `_div(${r.name}, mktcap)`;
    P.push({ name: r.name, expr, family: fam, kind: 'slow', positive: false, lookback: 1 });
    if (!ratioLike.test(r.name) && !perShare.test(r.name)) P.push({ name: `${r.name}_to_assets`, expr: `_div(${r.name}, total_assets)`, family: fam, kind: 'slow', positive: false, lookback: 1 });
  }
  return P;
}

// Gates: conditions that switch a signal on for a subset of stock-days.
const GATES = [
  { name: 'spx_down', expr: '(ret1_spx < 0) * np.ones_like(close) > 0', family: 'macro' },
  { name: 'spx_up', expr: '(ret1_spx > 0) * np.ones_like(close) > 0', family: 'macro' },
  { name: 'vix_high', expr: '(close_vix > ts_mean(close_vix, 66)) * np.ones_like(close) > 0', family: 'macro', lookback: 66 },
  { name: 'vix_low', expr: '(close_vix <= ts_mean(close_vix, 66)) * np.ones_like(close) > 0', family: 'macro', lookback: 66 },
  { name: 'pre_earnings', expr: '(trading_days_until_next_earnings_announcement >= 0) & (trading_days_until_next_earnings_announcement <= 10)', family: 'season' },
  { name: 'no_earnings', expr: 'trading_days_until_next_earnings_announcement > 10', family: 'season' },
  { name: 'month_end', expr: '(days_until_last_trading_day_of_month <= 3) * np.ones_like(close) > 0', family: 'season' },
  { name: 'large_cap', expr: 'cs_rank(mktcap) > 1.5', family: 'size' },
  { name: 'small_cap', expr: 'cs_rank(mktcap) <= 1.5', family: 'size' },
  { name: 'high_vol', expr: 'cs_rank(ts_std(ret1, 22)) > 1.5', family: 'risk', lookback: 23 },
  { name: 'low_vol', expr: 'cs_rank(ts_std(ret1, 22)) <= 1.5', family: 'risk', lookback: 23 },
  { name: 'high_volume_surprise', expr: 'cs_rank(_div(volume, ts_mean(volume, 22))) > 1.5', family: 'liquidity', lookback: 22 },
];

// ---------------------------------------------------------------- trees
// Leaf: {t:'leaf', p:<primitive name>, tf:<transform>, w}
// Unary: {t:'un', op, w?, a}   Binary: {t:'bin', op, a, b}   Gate: {t:'gate', g, a}
const LEAF_TF_DAILY = ['raw', 'mean', 'ema', 'zscore', 'tsrank', 'dev', 'std'];
const LEAF_TF_POSITIVE = ['surprise', 'zscore', 'tsrank', 'mean'];
const LEAF_TF_SLOW = ['raw', 'raw', 'yoy', 'tsrank'];

// Optional primitive weights (novel-hit rates) set by the search; uniform when absent.
let leafWeight = null;
function setLeafWeight(fn) { leafWeight = fn; }
function weightedPick(r, list) {
  if (!leafWeight) return pick(r, list);
  const w = list.map(p => leafWeight(p.name)); const sum = w.reduce((a, b) => a + b, 0);
  let x = r() * sum; for (let i = 0; i < list.length; i++) { x -= w[i]; if (x <= 0) return list[i]; }
  return list[list.length - 1];
}
function randomLeaf(r, P, family) {
  const pool = family ? P.filter(p => p.family === family) : P;
  const p = weightedPick(r, pool.length ? pool : P);
  const tf = p.kind === 'slow' ? pick(r, LEAF_TF_SLOW) : pick(r, p.positive ? [...LEAF_TF_DAILY, ...LEAF_TF_POSITIVE] : LEAF_TF_DAILY);
  return { t: 'leaf', p: p.name, tf, w: tf === 'raw' || tf === 'yoy' ? null : (p.kind === 'slow' ? 252 : pick(r, WINDOWS)) };
}

// Shape weights: the pilot showed leaves and single wrappers hit most often, gates never.
const SHAPE = { leaf: 0.45, un: 0.75, bin: 0.97 };
function randomTree(r, P, opts = {}, depth = 0) {
  const x = r();
  if (depth >= 2 || x < SHAPE.leaf) return randomLeaf(r, P, opts.family);
  if (x < SHAPE.un) return { t: 'un', op: pick(r, ['neg', 'smooth', 'ema', 'signlog']), w: pick(r, SHORT_WINDOWS), a: randomTree(r, P, opts, depth + 1) };
  if (x < SHAPE.bin) return { t: 'bin', op: pick(r, ['add', 'sub', 'mul']), a: randomTree(r, P, opts, depth + 1), b: randomTree(r, P, {}, depth + 1) };
  return { t: 'gate', g: pick(r, GATES).name, a: randomTree(r, P, opts, depth + 1) };
}

// ---------------------------------------------------------------- rendering
function renderLeaf(node, byName) {
  const p = byName[node.p];
  const e = p.expr, w = node.w;
  switch (node.tf) {
    case 'raw': return e;
    case 'mean': return `ts_mean(${e}, ${w})`;
    case 'ema': return `ts_mean_exp(${e}, ${w}, ${Math.min(0.9, +(2 / w).toFixed(3))})`;
    case 'zscore': return `ts_zscore(${e}, ${w})`;
    case 'tsrank': return `ts_rank(${e}, ${w})`;
    case 'dev': return `(${e} - ts_mean(${e}, ${w}))`;
    case 'std': return `ts_std(${e}, ${w})`;
    case 'surprise': return `_div(${e}, ts_mean(${e}, ${w}))`;
    case 'yoy': return `(${e} - ts_delay(${e}, 252))`;
    default: throw new Error(`unknown transform ${node.tf}`);
  }
}

function render(node, byName) {
  switch (node.t) {
    case 'leaf': return renderLeaf(node, byName);
    case 'un': {
      const a = render(node.a, byName);
      if (node.op === 'neg') return `(0.0 - ${a})`;
      if (node.op === 'smooth') return `ts_mean(${a}, ${node.w})`;
      if (node.op === 'ema') return `ts_mean_exp(${a}, ${node.w}, ${Math.min(0.9, +(2 / node.w).toFixed(3))})`;
      if (node.op === 'signlog') return `at_signlog(${a})`;
      break;
    }
    case 'bin': {
      const a = `cs_zscore(${render(node.a, byName)})`, b = `cs_zscore(${render(node.b, byName)})`;
      if (node.op === 'add') return `(${a} + ${b})`;
      if (node.op === 'sub') return `(${a} - ${b})`;
      if (node.op === 'mul') return `((cs_rank(${render(node.a, byName)}) - 1.5) * (cs_rank(${render(node.b, byName)}) - 1.5))`;
      break;
    }
    case 'gate': {
      const g = GATES.find(x => x.name === node.g);
      return `np.where(${g.expr}, ${render(node.a, byName)}, np.nan)`;
    }
  }
  throw new Error(`bad node ${JSON.stringify(node)}`);
}

const PRELUDE = 'def _div(a, b):\n    ok = np.abs(b) > 1e-9\n    return np.where(ok, a / np.where(ok, b, 1.0), np.nan)\n';

function toCode(tree, byName, sign = 1) {
  const body = render(tree, byName);
  return `${PRELUDE}alpha = ${sign < 0 ? '(0.0 - cs_rank(' + body + '))' : 'cs_rank(' + body + ')'}`;
}

function lookback(node, byName) {
  switch (node.t) {
    case 'leaf': {
      const base = byName[node.p].lookback;
      if (node.tf === 'yoy') return base + 252;
      return base + (node.w ? node.w - 1 : 0) + (node.tf === 'ema' ? node.w : 0);
    }
    case 'un': return lookback(node.a, byName) + (node.op === 'smooth' || node.op === 'ema' ? node.w : 0);
    case 'bin': return Math.max(lookback(node.a, byName), lookback(node.b, byName));
    case 'gate': return Math.max(lookback(node.a, byName), (GATES.find(x => x.name === node.g).lookback || 0) + 1);
  }
  return 1;
}

function leaves(node, out = []) {
  if (node.t === 'leaf') out.push(node); else { if (node.a) leaves(node.a, out); if (node.b) leaves(node.b, out); }
  return out;
}
function size(node) { return node.t === 'leaf' ? 1 : 1 + size(node.a) + (node.b ? size(node.b) : 0); }
function families(node, byName) { return [...new Set(leaves(node).map(l => byName[l.p].family))].sort(); }
function hashTree(tree, sign = 1) { return crypto.createHash('sha1').update(JSON.stringify([tree, sign])).digest('hex').slice(0, 12); }
const clone = x => JSON.parse(JSON.stringify(x));

// ---------------------------------------------------------------- variation
function nodes(node, out = [], parent = null, key = null) {
  out.push({ node, parent, key });
  if (node.a) nodes(node.a, out, node, 'a');
  if (node.b) nodes(node.b, out, node, 'b');
  return out;
}

function mutate(r, tree, P, byName) {
  const t = clone(tree);
  const all = nodes(t);
  const target = pick(r, all);
  const kind = r();
  if (kind < 0.25) { // window change
    const withW = all.filter(x => x.node.w);
    if (withW.length) { const x = pick(r, withW); x.node.w = byName[x.node.p]?.kind === 'slow' ? 252 : pick(r, x.node.t === 'leaf' ? WINDOWS : SHORT_WINDOWS); return t; }
  }
  if (kind < 0.5) { // swap primitive within family (or anywhere)
    const lv = leaves(t);
    const l = pick(r, lv);
    const fam = byName[l.p].family;
    const same = P.filter(p => p.family === fam && p.kind === byName[l.p].kind);
    l.p = pick(r, r() < 0.7 && same.length ? same : P.filter(p => p.kind === byName[l.p].kind)).name;
    return t;
  }
  if (kind < 0.65) { // wrap
    return { t: 'un', op: pick(r, ['smooth', 'ema', 'neg', 'signlog']), w: pick(r, SHORT_WINDOWS), a: t };
  }
  if (kind < 0.75) { // gate
    return { t: 'gate', g: pick(r, GATES).name, a: t.t === 'gate' ? t.a : t };
  }
  if (kind < 0.85 && target.parent) { // replace a subtree
    target.parent[target.key] = randomTree(r, P, {}, 1);
    return t;
  }
  // transform change on a leaf
  const l = pick(r, leaves(t));
  const p = byName[l.p];
  l.tf = p.kind === 'slow' ? pick(r, LEAF_TF_SLOW) : pick(r, p.positive ? [...LEAF_TF_DAILY, ...LEAF_TF_POSITIVE] : LEAF_TF_DAILY);
  l.w = l.tf === 'raw' || l.tf === 'yoy' ? null : (p.kind === 'slow' ? 252 : pick(r, WINDOWS));
  return t;
}

// Variants of a hit aimed at lower turnover / higher IR per sqrt(turnover), or small robustness moves.
function tvrVariant(r, tree, byName) {
  const t = clone(tree);
  const x = r();
  if (x < 0.45) { const w = pick(r, [3, 5, 10, 22]); return r() < 0.5 ? { t: 'un', op: 'smooth', w, a: t } : { t: 'un', op: 'ema', w, a: t }; }
  const withW = nodes(t).filter(n => n.node.w && (n.node.t === 'leaf' ? byName[n.node.p]?.kind !== 'slow' : ['smooth', 'ema'].includes(n.node.op)));
  if (x < 0.8 && withW.length) { const n = pick(r, withW).node; const grid = n.t === 'leaf' ? WINDOWS : SHORT_WINDOWS; const i = grid.indexOf(n.w); n.w = grid[Math.min(grid.length - 1, Math.max(0, i + (r() < 0.7 ? 1 : -1)))] || n.w; return t; }
  const raw = leaves(t).filter(l => l.tf === 'raw' && byName[l.p].kind === 'daily');
  if (raw.length) { const l = pick(r, raw); l.tf = pick(r, ['mean', 'ema']); l.w = pick(r, [5, 10, 22]); return t; }
  return { t: 'un', op: 'ema', w: pick(r, [5, 10]), a: t };
}

// Equal-weight composite of already-signed components.
function compose(parts) {
  const signed = parts.map(p => (p.sign < 0 ? { t: 'un', op: 'neg', w: 3, a: clone(p.tree) } : clone(p.tree)));
  return signed.slice(1).reduce((acc, b) => ({ t: 'bin', op: 'add', a: acc, b }), signed[0]);
}

function crossover(r, a, b) {
  return { t: 'bin', op: pick(r, ['add', 'add', 'sub', 'mul']), a: clone(a), b: clone(b) };
}

module.exports = { setLeafWeight, primitives, GATES, SHAPE, randomTree, randomLeaf, mutate, crossover, tvrVariant, compose, toCode, lookback, families, size, hashTree, rng, pick, clone };
