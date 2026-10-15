const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const FACTORY = path.join(ROOT, 'alphas', 'factory');
const GENERATOR_VERSION = 1;
const CLUSTERS = [
  'intraday', 'seasonality', 'fundamental_cash', 'fundamental_earnings',
  'fundamental_sales', 'fundamental_net_income', 'fundamental_assets',
  'fundamental_debt', 'fundamental_equity', 'fundamental_expenses',
  'fundamental_year', 'macro', 'price_volume',
];

function rel(file) { return path.relative(ROOT, file).replaceAll(path.sep, '/'); }
function read(file) { return fs.readFileSync(path.join(ROOT, file), 'utf8'); }
function json(file) { return JSON.parse(read(file)); }
function hashText(text) { return crypto.createHash('sha256').update(text).digest('hex'); }
function hashFile(file) { return hashText(read(file)); }
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])]));
  }
  return value;
}
function stringify(value) { return `${JSON.stringify(stable(value), null, 2)}\n`; }
function write(file, content) {
  const target = path.join(ROOT, file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
}
function source(file) { return { path: file, sha256: hashFile(file) }; }

function classify(item) {
  if (item.data_types === 'Technical' && ['GROUP_backoffice', 'GROUP_backoffice_derived'].includes(item.groupname)) return 'price_volume';
  if (item.data_types === 'Technical' && item.groupname === 'GROUP_intra1') return 'intraday';
  if (item.data_types === 'Seasonality') return 'seasonality';
  if (['Macro', 'ETF'].includes(item.data_types)) return 'macro';
  if (item.data_types === 'Fundamental') return `fundamental_${json('fundamental_themes.json')[item.varname]}`;
  throw new Error(`Cannot classify field ${item.varname}`);
}
function frequency(days) {
  const n = Number(days);
  return n <= 3 ? 'daily' : n <= 40 ? 'monthly' : n <= 100 ? 'quarterly' : 'annual';
}
function caveats(item) {
  const out = [];
  if (item.is_derived === 1) out.push('derived');
  if (item.delay_0 === 0) out.push('timing review required; do not auto-delay');
  if (Number(item.coverage) < 500) out.push(`sparse coverage (${Number(item.coverage)})`);
  if (item.empty_value !== '' && item.empty_value != null) out.push(`missing encoded as ${item.empty_value}`);
  if (item.adjfactor_type) out.push('corporate-action adjusted');
  if (item.groupname === 'GROUP_fred') out.push('forward-filled from lower-frequency observations');
  return out;
}
function short(text, length = 150) {
  const compact = String(text || '').replace(/\s+/g, ' ').trim()
    .replace(/^This (?:variable|field) (?:represents|provides|indicates|reflects|is|includes|measures) /i, '');
  return compact.length <= length ? compact : `${compact.slice(0, length - 1).trim()}…`;
}
function parseClusterHeader(markdown) {
  const title = markdown.match(/^# (.+?)\s+\(\d+ vars\)/m)?.[1];
  const status = markdown.match(/^\*\*Status:\*\* (.+)$/m)?.[1];
  const notes = markdown.match(/^\*\*Notes:\*\* (.+)$/m)?.[1];
  if (!title || !status || !notes) throw new Error('Malformed data-map cluster header');
  return { title, status, notes };
}

const mechanisms = {
  intraday: ['session handoff', 'opening/closing pressure', 'range position', 'liquidity shock', 'risk-adjusted reversal/continuation'],
  seasonality: ['event proximity gate', 'month/quarter boundary', 'earnings calendar state', 'options-expiry regime'],
  macro: ['market-regime gate', 'volatility-state interaction', 'index/ETF shock conditioning', 'slow macro state tilt'],
  price_volume: ['return reversal/continuation', 'volume-price interaction', 'range displacement', 'liquidity/size conditioning'],
  fundamental_cash: ['cash quality', 'cash-flow yield', 'financing/investment divergence', 'liquidity resilience'],
  fundamental_earnings: ['earnings quality', 'profitability change', 'estimate surprise/persistence', 'valuation interaction'],
  fundamental_sales: ['sales growth', 'margin efficiency', 'revenue surprise', 'asset-turnover interaction'],
  fundamental_net_income: ['income quality', 'profit acceleration', 'reported/normalized divergence', 'income yield'],
  fundamental_assets: ['asset efficiency', 'investment growth', 'asset composition', 'valuation-to-assets'],
  fundamental_debt: ['leverage stress', 'debt-service capacity', 'liability change', 'credit-quality interaction'],
  fundamental_equity: ['book-value yield', 'ROE quality', 'retained-earnings change', 'capital-structure interaction'],
  fundamental_expenses: ['cost efficiency', 'expense growth', 'operating leverage', 'margin pressure'],
  fundamental_year: ['year-over-year change', 'annual persistence', 'reporting-cycle state', 'fundamental acceleration'],
};

function externalFields(cluster) {
  const common = [
    { field: 'industry', cluster: 'price_volume', use: 'group neutralization only' },
    { field: 'sector', cluster: 'price_volume', use: 'group neutralization only' },
    { field: 'mktcap', cluster: 'price_volume', use: 'size conditioning or normalization' },
    { field: 'ret1', cluster: 'price_volume', use: 'stock-level return conditioning' },
  ];
  if (cluster === 'price_volume') return [
    { field: 'day_of_the_week', cluster: 'seasonality', use: 'calendar regime gate' },
    { field: 'close_vix', cluster: 'macro', use: 'market-volatility regime interaction' },
  ];
  if (cluster === 'macro') return common.slice(0, 3);
  if (cluster === 'seasonality') return common;
  return common;
}

function lookbacks(cluster) {
  if (cluster === 'macro') return { sensible_windows_days: [5, 22, 66, 252], note: 'Use short windows only for daily index/ETF observations; slow FRED levels are regime states.' };
  if (cluster.startsWith('fundamental_')) return { sensible_windows_days: [22, 66, 126, 252], note: 'Sparse quarterly/annual step functions need coarse horizons; respect reporting availability.' };
  if (cluster === 'seasonality') return { sensible_windows_days: [5, 22, 66, 252], note: 'Match the window to the event cycle; event flags are normally gates.' };
  return { sensible_windows_days: [5, 22, 66], note: 'Use coarse windows; nearby-window sweeps are cosmetic unless tied to a timing hypothesis.' };
}

function buildContexts() {
  const distribution = json('data-distribution.json').items;
  const byCluster = Object.fromEntries(CLUSTERS.map(cluster => [cluster, []]));
  for (const item of distribution) byCluster[classify(item)].push(item);
  const outputs = {};
  for (const cluster of CLUSTERS) {
    const mapPath = `data-map/clusters/${cluster}.md`;
    const header = parseClusterHeader(read(mapPath));
    const fields = byCluster[cluster].sort((a, b) => a.varname.localeCompare(b.varname)).map(item => ({
      name: item.varname,
      value_type: item.value_type || null,
      dimensionality: cluster === 'macro' ? 'market-wide' : item.dimensions === '2D' ? 'cross-sectional' : 'market-wide',
      units: item.units || 'unspecified',
      availability: {
        frequency: frequency(item.update_frequency),
        approximate_update_days: Number(item.update_frequency),
        coverage_count: Number(item.coverage),
      },
      caveats: caveats(item),
    }));
    outputs[`alphas/factory/context/${cluster}.json`] = {
      schema_version: 1,
      generator_version: GENERATOR_VERSION,
      cluster,
      purpose: short(header.notes, 220),
      catalog_status: header.status,
      permitted_primary_fields: fields,
      lookbacks: lookbacks(cluster),
      permitted_cross_cluster_external_fields: externalFields(cluster),
      cross_cluster_limit: 'At most one justified external term; the primary mechanism must remain cluster-native.',
      mechanism_families_worth_testing: mechanisms[cluster],
      known_invalid_or_redundant_constructions: [
        ...(cluster === 'macro' ? ['Ranking a market-wide series or using it alone as a stock signal.', 'High-turnover transforms of forward-filled FRED levels.'] : []),
        ...(cluster === 'seasonality' ? ['Using a market-wide calendar flag alone without a stock-level signal.'] : []),
        ...(cluster === 'price_volume' ? ['Cosmetic recreation of picked-over 101 formulas without a new mechanism.'] : []),
        'Combining incompatible units without ranking, scaling, or forming a dimensionless ratio.',
        'Ranking categorical sector/industry/subindustry identifiers.',
        'Nearby-window, wrapper-only, sign-only, or renamed duplicates without a stated behavioral question.',
      ],
      sources: [source(mapPath), source('data-distribution.json'), source('fundamental_themes.json')],
    };
  }
  return outputs;
}

function parameterLines(text, heading) {
  const block = text.match(new RegExp(`\\*\\*${heading}\\*\\*:?\\n([\\s\\S]*?)(?:\\n\\n\\*\\*|\\n\\n#|$)`, 'i'))?.[1] || '';
  return block.split('\n').map(line => line.match(/^\s*-\s*`?([^`:]+)`?:?\s*(.+)$/)).filter(Boolean)
    .map(match => ({ name: match[1].trim(), expectation: short(match[2], 180) }));
}
function signatureArguments(signature) {
  const body = signature.slice(signature.indexOf('(') + 1, -1);
  const args = [];
  let depth = 0;
  let start = 0;
  for (let index = 0; index < body.length; index += 1) {
    if ('[({'.includes(body[index])) depth += 1;
    if (']})'.includes(body[index])) depth -= 1;
    if (body[index] === ',' && depth === 0) {
      args.push(body.slice(start, index).trim());
      start = index + 1;
    }
  }
  if (body.trim()) args.push(body.slice(start).trim());
  return args;
}
function operatorDetails(full, summary) {
  // Keep the behavioural facts the one-line summary drops (output ranges, NaN handling, units),
  // e.g. cs_rank "scale uniformly between 1 and 2". Parameters/Returns are captured separately.
  const paragraphs = full.split(/\n\s*\n/).map(text => text.trim()).filter(Boolean);
  const body = paragraphs.filter(text => text !== (summary || '').trim() && !/^\*\*(Parameters|Returns|Notes|Examples?)\*\*/.test(text) && !text.startsWith('```') && !text.startsWith('- `'));
  const notesIndex = paragraphs.findIndex(text => /^\*\*Notes\*\*/.test(text));
  const out = {};
  if (body.length) out.details = short(body[0].replace(/\s+/g, ' '), 220);
  if (notesIndex >= 0 && paragraphs[notesIndex + 1] && !paragraphs[notesIndex + 1].startsWith('```') && paragraphs[notesIndex + 1].trim() !== body[0]) out.notes = short(paragraphs[notesIndex + 1].replace(/\s+/g, ' '), 220);
  return out;
}

function buildOperators() {
  const file = 'built-in-operators.json';
  const input = json(file);
  const operators = input.items.map(item => {
    const full = item.oper_full_desc || '';
    const signature = item.oper_name;
    const name = signature.split('(')[0];
    const args = signatureArguments(signature);
    const windowed = name.startsWith('ts_') && args.some(arg => /days|\bn\b/.test(arg));
    return {
      name,
      signature,
      arity: args.length,
      category: name.startsWith('ts_') ? 'time-series' : name.startsWith('cs_') ? 'cross-sectional' : 'element-wise',
      inputs: parameterLines(full, 'Parameters'),
      outputs: parameterLines(full, 'Returns'),
      lookback_restrictions: windowed ? 'Positive integer window; contributes window - 1 days (or delay n) to the deepest dependency.' : 'No rolling lookback parameter.',
      constraints: short(item.oper_desc, 180),
      ...operatorDetails(full, item.oper_desc),
    };
  });
  return {
    schema_version: 1,
    generator_version: GENERATOR_VERSION,
    source: source(file),
    operators,
  };
}

function metricEnvelope(run) {
  if (!run) return { status: 'absent', metrics: null };
  const result = run.result || null;
  return {
    status: run.status,
    metrics: result ? { id: result.id ?? null, ir: result.ir ?? null, turnover: result.turnover ?? null, ir_sqrt_turnover: result.ir_tvr ?? null } : null,
  };
}
function formulaFingerprint(code) {
  const canonical = String(code || '').replace(/#.*$/gm, '').replace(/\s+/g, ' ').trim();
  return hashText(canonical);
}
function structuralFingerprint(code) {
  return hashText(String(code || '').replace(/#.*$/gm, '').replace(/[a-z][a-z0-9_]*/gi, 'X').replace(/\d+(?:\.\d+)?/g, 'N').replace(/\s+/g, ' ').trim());
}
function fieldFingerprint(fields) { return hashText([...fields].sort().join('\n')); }
function operatorFingerprint(code) {
  return hashText([...new Set((code || '').match(/\b(?:at|cs|ts)_[a-z0-9_]+(?=\s*\()/g) || [])].sort().join('\n'));
}
function buildAttempts() {
  const directory = path.join(ROOT, 'alphas', 'research', 'candidates');
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory).filter(file => file.endsWith('.json')).sort().map(file => {
    const candidate = JSON.parse(fs.readFileSync(path.join(directory, file), 'utf8'));
    const fields = [...(candidate.inputs?.primary_variables || []), ...(candidate.inputs?.secondary_variables || [])].sort();
    const operators = [...new Set((candidate.code || '').match(/\b(?:at|cs|ts)_[a-z0-9_]+(?=\s*\()/g) || [])].sort();
    return {
      id: candidate.candidate_id,
      lineage: candidate.lineage,
      role: candidate.lineage?.generation === 0 ? 'root' : 'variant',
      cluster: candidate.inputs?.primary_cluster,
      mechanism_class: candidate.metadata?.mechanism_classification || null,
      canonical_formula_hash: formulaFingerprint(candidate.code),
      structural_fingerprint: structuralFingerprint(candidate.code),
      field_fingerprint: fieldFingerprint(fields),
      operator_fingerprint: operatorFingerprint(candidate.code),
      tags: {
        gate: candidate.metadata?.behavioral_axes?.conditioning_state || null,
        neutralization: candidate.metadata?.behavioral_axes?.exposure_treatment || (candidate.metadata?.neutralized ? 'neutralized' : 'raw'),
        horizon: candidate.metadata?.behavioral_axes?.horizon || null,
        topology: candidate.metadata?.mechanism_classification || null,
      },
      fast: metricEnvelope(candidate.runs?.fast),
      slow: metricEnvelope(candidate.runs?.slow),
      disposition: candidate.status,
      location: { kind: 'live', candidate: `alphas/research/candidates/${file}` },
      created_timestamp: candidate.created_at
        || candidate.runs?.fast?.provenance?.batch?.created_at
        || candidate.runs?.slow?.provenance?.batch?.created_at
        || null,
    };
  });
}

function latestFirst(left, right) {
  return String(right.created_timestamp || '').localeCompare(String(left.created_timestamp || '')) || left.id.localeCompare(right.id);
}
function attemptBrief(row) {
  return {
    id: row.id,
    family_id: row.lineage?.family_id || null,
    cluster: row.cluster,
    mechanism_class: row.mechanism_class,
    structural_fingerprint: row.structural_fingerprint,
    disposition: row.disposition,
    fast_ir: row.fast?.metrics?.ir ?? null,
    slow_ir: row.slow?.metrics?.ir ?? null,
  };
}
function boundedGroups(attempts, keyFunction, minimumSize, groupLimit = 12, memberLimit = 6) {
  const groups = new Map();
  for (const row of attempts) {
    const key = keyFunction(row);
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return [...groups.entries()].filter(([, rows]) => rows.length >= minimumSize)
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
    .slice(0, groupLimit)
    .map(([key, rows]) => ({ key, total: rows.length, attempts: rows.sort(latestFirst).slice(0, memberLimit).map(attemptBrief) }));
}
function buildAttemptSummary(attempts, campaign, activeBatch) {
  const activeCluster = campaign.current_cluster;
  const activeIds = new Set(activeBatch.root_to_variant_decisions.map(item => item.candidate_id));
  const failed = attempts.filter(row => ['fast_error', 'fast_rejected', 'slow_error', 'slow_rejected'].includes(row.disposition));
  return {
    schema_version: 1,
    generator_version: GENERATOR_VERSION,
    full_index: { path: 'alphas/factory/attempt-index.jsonl', role: 'machine_memory_do_not_load_into_generation_prompt' },
    total_attempts: attempts.length,
    active_cluster: activeCluster,
    structural_duplicate_groups: boundedGroups(attempts, row => row.structural_fingerprint, 2),
    same_cluster_mechanism_families: activeCluster
      ? boundedGroups(attempts.filter(row => row.cluster === activeCluster), row => `${row.cluster}:${row.mechanism_class || 'unclassified'}`, 1)
      : [],
    recent_failed_families: failed.sort(latestFirst).slice(0, 24).map(attemptBrief),
    active_batch_nearby_candidates: attempts.filter(row => activeIds.has(row.id)).sort(latestFirst).slice(0, 48).map(attemptBrief),
    limits: { duplicate_groups: 12, mechanism_families: 12, attempts_per_group: 6, recent_failures: 24, active_batch_candidates: 48 },
    duplicate_check_command: 'node scripts/trexsim-check-factory-duplicate.js <candidate.json>',
    source: { path: 'alphas/factory/attempt-index.jsonl', sha256: hashText(attempts.map(row => JSON.stringify(stable(row))).join('\n') + (attempts.length ? '\n' : '')) },
  };
}

function buildFrontier() {
  const poolPath = 'alphas/research/legacy-optimal-pool.json';
  const corrPath = 'alphas/research/legacy-slow-correlation.json';
  const pool = json(poolPath);
  const corr = json(corrPath);
  const alphaById = new Map((corr.alphas || []).map(alpha => [String(alpha.id), alpha]));
  const baseline = pool.submission_order.map(item => {
    const alpha = alphaById.get(String(item.id));
    const pnl = alpha?.source_pnl_csv || alpha?.pnl_file || alpha?.archive_pnl_csv || alpha?.path || `trexsim:slow:${item.id}`;
    return {
      id: String(item.id),
      name: item.name,
      source_category: 'legacy',
      slow_ir: item.ir,
      turnover: item.tvr,
      ir_sqrt_turnover: item.ir_tvr,
      qualified: Number(item.ir) > 0.07,
      order: item.order,
      admission: item.admission,
      predecessors: item.correlated_prior || [],
      pnl_reference: pnl,
    };
  });
  const candidateDir = path.join(ROOT, 'alphas', 'research', 'candidates');
  const liveRecords = fs.existsSync(candidateDir)
    ? fs.readdirSync(candidateDir).filter(file => file.endsWith('.json')).sort().map(file => JSON.parse(fs.readFileSync(path.join(candidateDir, file), 'utf8')))
    : [];
  const liveSelected = new Set();
  const livePoolPath = path.join(ROOT, 'alphas', 'research', 'optimal-pool.json');
  if (fs.existsSync(livePoolPath)) {
    for (const item of JSON.parse(fs.readFileSync(livePoolPath, 'utf8')).submission_order || []) {
      if (item.source !== 'legacy' && item.name) liveSelected.add(item.name);
    }
  }
  function compactLive(candidate) {
    const slow = candidate.runs?.slow?.result || {};
    return {
      id: candidate.candidate_id,
      source_category: 'live_research',
      slow_ir: slow.ir ?? null,
      turnover: slow.turnover ?? null,
      ir_sqrt_turnover: slow.ir_tvr ?? null,
      qualified: Number(slow.ir) > 0.07,
      order: null,
      admission: null,
      predecessors: [],
      pnl_reference: slow.archive_pnl_csv || (slow.id ? `trexsim:slow:${slow.id}` : null),
    };
  }
  const submitted = liveRecords.filter(candidate => candidate.status === 'submitted').map(compactLive);
  const selected = liveRecords.filter(candidate => candidate.status === 'qualified' && liveSelected.has(candidate.candidate_id)).map(compactLive);
  const reorderable = liveRecords.filter(candidate => candidate.status === 'qualified' && !liveSelected.has(candidate.candidate_id)).map(compactLive);
  return {
    schema_version: 1,
    generator_version: GENERATOR_VERSION,
    baseline_identity: 'legacy-101-selected-9',
    baseline_scope: 'The nine-alpha legacy selected pool only; it is not the full legacy qualified universe.',
    full_legacy_qualified_universe_reference: corrPath,
    ordering_assumption: 'Legacy selection is a reorderable theoretical optimum, not evidence of an already-submitted fixed prefix.',
    fixed_already_submitted_prefix: submitted,
    legacy_selected_baseline: baseline,
    reorderable_theoretical_pool_candidates: reorderable,
    current_live_research_candidates: selected,
    sources: [source(poolPath), source(corrPath)],
  };
}

function emptyClusterScore(cluster) {
  return {
    roots_tested: 0,
    fast: { valid: 0, pass: 0, potential: 0, promoted: 0 },
    slow: { tested: 0, qualified: 0 },
    exact_pool_additions: 0,
    novel_pnl_neighborhoods: 0,
    duplication_collision_rate: null,
    costs: { fast_runs: 0, slow_runs: 0, errors: 0 },
    recommended_next_allocation: cluster === 'price_volume' ? 'deprioritize_primary; use chiefly as an external/base term' : 'breadth-first root sample',
    confidence: 'none',
    sample_size_warning: 'No live non-legacy attempts; allocation evidence is not yet available.',
  };
}

function buildScoreboard(attempts) {
  const clusters = Object.fromEntries(CLUSTERS.map(cluster => [cluster, emptyClusterScore(cluster)]));
  for (const row of attempts) {
    const score = clusters[row.cluster];
    if (!score) continue;
    if (row.role === 'root' && !['pending', 'absent'].includes(row.fast.status)) score.roots_tested += 1;
    if (row.fast.status === 'success') {
      score.fast.valid += 1;
      if (Number(row.fast.metrics?.ir) >= 0.035) score.fast.pass += 1;
      if (Number(row.fast.metrics?.ir) >= 0.035 && Number(row.fast.metrics?.ir) < 0.05) score.fast.potential += 1;
      if (Number(row.fast.metrics?.ir) >= 0.05) score.fast.promoted += 1;
      score.costs.fast_runs += 1;
    } else if (row.fast.status === 'error') {
      score.costs.fast_runs += 1;
      score.costs.errors += 1;
    }
    if (row.slow.status === 'success') {
      score.slow.tested += 1;
      score.costs.slow_runs += 1;
      if (Number(row.slow.metrics?.ir) > 0.07) score.slow.qualified += 1;
    } else if (row.slow.status === 'error') {
      score.slow.tested += 1;
      score.costs.slow_runs += 1;
      score.costs.errors += 1;
    }
  }
  const frontier = buildFrontier();
  for (const row of [...frontier.current_live_research_candidates, ...frontier.fixed_already_submitted_prefix]) {
    const attempt = attempts.find(item => item.id === row.id);
    if (attempt && clusters[attempt.cluster]) clusters[attempt.cluster].exact_pool_additions += 1;
  }
  const researchDir = path.join(ROOT, 'alphas', 'research');
  for (const cluster of CLUSTERS) {
    const reviews = fs.readdirSync(researchDir).filter(file => file.startsWith(cluster) && file.endsWith('diversity-review.json')).sort();
    for (const file of reviews) {
      const review = JSON.parse(fs.readFileSync(path.join(researchDir, file), 'utf8'));
      const neighborhoodCount = Number(review.behavioral_neighborhoods);
      if (Number.isFinite(neighborhoodCount)) clusters[cluster].novel_pnl_neighborhoods = Math.max(clusters[cluster].novel_pnl_neighborhoods, neighborhoodCount);
      const collisionRate = Number(review.within_relevant_roots?.proportion_above_0_50);
      if (Number.isFinite(collisionRate)) clusters[cluster].duplication_collision_rate = collisionRate;
    }
  }
  for (const score of Object.values(clusters)) {
    const sample = score.fast.valid;
    score.confidence = sample >= 30 ? 'moderate' : sample >= 10 ? 'low' : 'none';
    score.sample_size_warning = sample >= 30 ? null : `Only ${sample} valid Fast observations; do not over-allocate from this sample.`;
    if (sample > 0) score.recommended_next_allocation = score.slow.qualified > 0
      ? 'adaptive follow-up based on measured PNL novelty and exact pool yield'
      : 'continue breadth-first sampling; evidence is not yet productive';
  }
  return {
    schema_version: 1,
    generated_from_live_candidates_only: true,
    allocation_policy: 'breadth-first across under-sampled clusters, then adapt using Slow pool additions, novel Fast PNL neighborhoods, collision rate, and cost',
    clusters,
    sources: [
      source('alphas/research/campaign.json'),
      ...attempts.map(row => source(row.location.candidate)),
      ...fs.readdirSync(researchDir).filter(file => file.endsWith('diversity-review.json')).sort().map(file => source(`alphas/research/${file}`)),
    ],
  };
}

function buildActiveBatch(campaign) {
  const candidateDir = path.join(ROOT, 'alphas', 'research', 'candidates');
  if (!fs.existsSync(candidateDir)) return {
    schema_version: 1,
    batch_ids: [], phase: 'none', counts: { candidates: 0, successes: 0, errors: 0 },
    fast_metrics: [], slow_metrics: [], behavioral_pnl_neighborhoods: [], frontier_collisions: [],
    root_to_variant_decisions: [], recommended_next_actions: [campaign.next_action], detailed_artifacts: [],
    note: 'No active live batch after the post-legacy reset.', sources: [source('alphas/research/campaign.json')],
  };
  const records = fs.readdirSync(candidateDir).filter(file => file.endsWith('.json')).sort().map(file => ({
    file: `alphas/research/candidates/${file}`,
    value: JSON.parse(fs.readFileSync(path.join(candidateDir, file), 'utf8')),
  }));
  const batches = [];
  for (const record of records) for (const mode of ['fast', 'slow']) {
    const batch = record.value.runs?.[mode]?.provenance?.batch;
    if (batch?.created_at) batches.push({ key: `${mode}:${batch.manifest_sha256 || batch.created_at}`, mode, batch });
  }
  if (!batches.length) return {
    schema_version: 1,
    batch_ids: [], phase: campaign.phase, counts: { candidates: 0, successes: 0, errors: 0 },
    fast_metrics: [], slow_metrics: [], behavioral_pnl_neighborhoods: [], frontier_collisions: [],
    root_to_variant_decisions: [], recommended_next_actions: [campaign.next_action],
    detailed_artifacts: records.map(record => record.file),
    note: 'Live candidates exist, but no batch provenance is available.',
    sources: [source('alphas/research/campaign.json'), ...records.map(record => source(record.file))],
  };
  batches.sort((a, b) => a.batch.created_at.localeCompare(b.batch.created_at) || a.key.localeCompare(b.key));
  const latest = batches.at(-1);
  const members = records.filter(record => {
    const batch = record.value.runs?.[latest.mode]?.provenance?.batch;
    return batch && `${latest.mode}:${batch.manifest_sha256 || batch.created_at}` === latest.key;
  });
  const metrics = members.map(record => {
    const run = record.value.runs?.[latest.mode];
    return {
      id: record.value.candidate_id,
      status: run?.status,
      ir: run?.result?.ir ?? null,
      turnover: run?.result?.turnover ?? null,
      ir_sqrt_turnover: run?.result?.ir_tvr ?? null,
      error: run?.error ?? null,
    };
  });
  const reviewFiles = fs.readdirSync(path.join(ROOT, 'alphas', 'research'))
    .filter(file => file.endsWith('diversity-review.json')).sort();
  const reviewFile = reviewFiles.at(-1) || null;
  const review = reviewFile ? json(`alphas/research/${reviewFile}`) : null;
  const neighborhoods = Array.isArray(review?.behavioral_neighborhoods)
    ? review.behavioral_neighborhoods
    : (review?.relevant_roots || []).map(item => item.neighborhood).filter(Boolean);
  const collisions = review?.legacy_frontier_collisions
    || (review?.variants || []).flatMap(item => item.legacy_frontier_collisions || [])
    || [];
  return {
    schema_version: 1,
    batch_ids: [latest.batch.manifest_sha256 || latest.batch.created_at],
    phase: latest.mode,
    counts: {
      candidates: members.length,
      successes: metrics.filter(item => item.status === 'success').length,
      errors: metrics.filter(item => item.status === 'error').length,
    },
    fast_metrics: latest.mode === 'fast' ? metrics : [],
    slow_metrics: latest.mode === 'slow' ? metrics : [],
    behavioral_pnl_neighborhoods: [...new Set(neighborhoods)],
    frontier_collisions: collisions,
    root_to_variant_decisions: members.map(record => ({
      root_id: record.value.lineage?.root_candidate_id || record.value.candidate_id,
      candidate_id: record.value.candidate_id,
      disposition: record.value.status,
    })),
    recommended_next_actions: [campaign.next_action],
    detailed_artifacts: [...members.map(record => record.file), ...(reviewFile ? [`alphas/research/${reviewFile}`] : [])],
    note: reviewFile ? 'Behavioral evidence is compacted from the latest live diversity review.' : 'Neighborhoods and frontier collisions remain empty until a live diversity review exists; never infer them from syntax.',
    sources: [source('alphas/research/campaign.json'), ...members.map(record => source(record.file)), ...(reviewFile ? [source(`alphas/research/${reviewFile}`)] : [])],
  };
}

function factoryAgent() {
  return "# Trex Alpha Factory Agent (v3)\n\n## Mission\n\nGrow the maximum valid submission pool. A candidate qualifies only with a valid **Slow IR strictly greater than 0.07**; nothing else about quality matters. Slots come from new independent trades (breadth) and from ladders that use the 1.2x override. Fast is cheap and steers the search; Slow is the budget and the only evidence that counts.\n\n## Read order and compact state\n\nRead, in order: this file; `state.json`; the assigned `context/<cluster>.json`; `master-frontier.json`; `active-batch-summary.json`; `operators-compact.json`; and `attempt-summary.json`. Use `cluster-scoreboard.json` when choosing allocation and `competition-compact.json` for machine-consumed rule checks. Do not load `attempt-index.jsonl`; it is machine memory for deterministic duplicate checks. These files are derived indexes: never add a metric that is absent from an authoritative candidate/result record. Follow `state.json.next_required_action` and stay within its budgets.\n\nNormally this compact package is the entire generation context. Consult `ALPHA_RESEARCH_AGENT.md` (authoritative, including its tooling-status section), `RESEARCH_CANDIDATE_FORMAT.md`, `ALPHA_RESEARCH_LESSONS.md`, `data-distribution.json`, `data-map/`, or `built-in-operators.json` only for a specific ambiguity. Do not load archived v1/v2 candidates or results into generation context.\n\n## Admission rule and the dead zone\n\nA new alpha is admitted if its Slow PNL correlation is **at most 0.50** with every submitted alpha, or its Slow **IR/sqrt(turnover) (q) is at least 1.2x** each correlated alpha's. The pool is fully reorderable; submit each correlated group in increasing q. For a correlated pair, ratio = q_new / q_old: at 1.2 or above, or at 0.83 or below, both fit; between 0.83 and 1.2 is the **dead zone**, where only one fits.\n\n## Cadence and budget\n\nOne cluster visit per day/night cycle. Fast (~15 s per run, one global queue) is cheap: do not ration it. Slow (~5 min per run, sequential, ~70-80 per night) is the budget. Day: plan, wave 1, triage, wave 2, triage, variants, triage. Evening: launch `node scripts/trexsim-run.js research-slow` in the foreground, piped through `tee` into `alphas/research/logs/` (background launches are killed); it runs the triage queue in priority order up to the nightly cap. If the shell tool returns control while it runs, wait only with `node scripts/trexsim-wait.js --mode slow --runs <N> --max-minutes <M>`, with M as long as your shell tool allows (ideally one call per night); never use `sleep`, short polling loops, or frequent wake-ups. Morning: ingest, rebuild the exact Slow matrix, run the optimizer, report the pool change, carry seeds and overflow forward.\n\n## Roots\n\nGenerate ~80 roots per visit in two waves of ~40 and ~30-40. Plan across information timing, economic event, continuation vs reversal, horizon, conditioning state, exposure treatment, and expected turnover; field substitution, nearby windows, wrappers, sign, and neutralization labels are not breadth. Wave 2 receives the wave-1 neighborhood summary and avoids crowded neighborhoods. About a fifth of roots should be cross-cluster constructions using the context's permitted external fields. Complexity is allowed when it serves IR or decorrelation. Fill `metadata.behavioral_axes` with short, consistent labels for economic_behavior, information_timing, horizon, conditioning_state, and expected_turnover. Before accepting each candidate, run `node scripts/trexsim-check-factory-duplicate.js <candidate.json>`.\n\n## Fast triage (scripted)\n\nAfter every Fast ingestion, and after the morning Slow ingestion, run `python3 scripts/trexsim-fast-triage.py` and start from `alphas/research/triage/latest-summary.md`; you may open `alphas/research/triage/latest.json` or your own candidate records to investigate. Never compute correlations, ratios, buckets, the Slow gate, or the Slow queue yourself. The summary gives crowded neighborhoods (steer wave 2 away from them), bucket counts, the Slow queue, variant seeds with the exact IR/sqrt(turnover) each must reach, a \"what worked\" table by behavioral axis, the top 10 candidates, and Fast-vs-Slow results for the latest Slow night. `research-slow` follows the queue automatically, including its order and nightly cap.\n\n## Reflection and research notes\n\nThink, do not only execute: the scripts do the arithmetic so your effort goes into explaining results and choosing what to try next. After every triage and every morning rebuild, write a note in `alphas/research/notes/` using the template in its README: what you tried, what the results say, why, concrete predictions, checks of earlier predictions, and the plan. Read the three most recent notes before planning a wave or a variant round. Notes are separate from `ALPHA_RESEARCH_LESSONS.md`, the human's global log; never edit that file, and propose durable findings under \"Candidate lessons for the human\".\n\n## Variants\n\nEvery variant names its target: ladder-up, ladder-down, escape-dead-zone, clear-ir-floor, decorrelate, or explore. Prefer turnover shaping (smoothing, ts_mean_exp, longer windows), then conditioning, then transforms; neutralization has had low yield. Build variants for seeds listed in the triage summary, plus up to about 15% free variants you justify from the results or your notes (`changes.purpose: \"explore\"`). Up to 6 variants per seed per round; another round is allowed while the last one made a Fast crossing. Slow near-misses (IR 0.055-0.07) and dead-zone Slow qualifiers are valid seeds. Parameter searches are allowed when they target a crossing. Do not sign-flip a positive seed. A variant is always a new record; never edit a completed candidate.\n\n## Valid generation\n\n- Produce a numeric stock-by-date matrix with usable cross-sectional variation. Market-wide fields must interact with a stock-level field; never rank market-wide series or categorical grouping IDs.\n- `cs_rank` and `ts_rank` return values in [1, 2], not [0, 1]: a percentile gate is `1 + p` (bottom 30% is `cs_rank(x) < 1.3`, top 10% is `> 1.9`). Check `details` in `operators-compact.json` for other operators' output ranges.\n- In an inactive signal gate use `np.nan`, never `0.0`: TrexSim median-centers values, so zero can still become a position. Never return a raw boolean.\n- Preserve units. Respect point-in-time availability, reporting lag, adjustments, missing encodings, and field caveats. No imports, side effects, future access, negative delays/windows, or centered/reverse windows.\n- Compute `required_lookback` as the deepest dependency plus one final-value day: add `window - 1` for rolling operations and `k` for `ts_delay(x, k)`; `ret1` consumes one prior day. Slow lookback is required lookback plus 5 days, or plus 10 when required lookback is at least 100.\n\nWhen compact data is insufficient, stop that formula and consult only the specific authoritative source needed; record the ambiguity rather than guessing.\n";
}

function buildAll() {
  const campaign = json('alphas/research/campaign.json');
  const attempts = buildAttempts();
  if (attempts.some(row => row.location.kind !== 'live')) throw new Error('Archived candidate leaked into live attempt index');
  const generatedAt = campaign.updated_at || campaign.created_at;
  const state = {
    schema_version: 1,
    current_phase: campaign.phase,
    active_cluster: campaign.current_cluster,
    budgets: {
      generation: { roots_per_visit: 80, waves: [40, 40], cross_cluster_share: 0.2, remaining_this_phase: campaign.phase === 'not_started' ? 80 : null },
      variants: { per_seed_per_round_max: 6, further_round_rule: 'allowed while the previous round made a Fast crossing', targets: ['ladder-up', 'ladder-down', 'escape-dead-zone', 'clear-ir-floor', 'decorrelate', 'explore'], free_variant_share: 0.15, slow_near_miss_seed_ir: [0.055, 0.07] },
      reflection: { notes_dir: 'alphas/research/notes', write_after: ['every triage', 'every morning rebuild'], read_recent: 3, never_edit: 'ALPHA_RESEARCH_LESSONS.md' },
      fast_triage: { new_max_corr: 0.45, ladder_ratio_min: 1.3, ladder_ratio_max_down: 0.77, dead_zone: [0.83, 1.2], neighborhood_corr: 0.5, crowded_min_size: 4 },
      slow_gate: { promote_min_fast_ir: 0.05, potential_min_fast_ir: 0.035, static_min_fast_ir: 0.072, potential_time_dependent_min_fast_ir: 0.045, near_miss_slow_ir: [0.055, 0.07], note: 'Applied by scripts/trexsim-fast-triage.py; static = no ts_* operators, loops, or np.roll.' },
      slow: { policy: 'priority-ordered overnight queue written by scripts/trexsim-fast-triage.py: new, ladder, marginal, potential (not dead), dead if capacity remains', nightly_cap: 70, overflow: 'carry to next night ahead of same-tier new items', remaining_this_phase: 0 },
    },
    baseline_identity: 'legacy-101-selected-9',
    next_required_action: campaign.next_action,
    last_updated: generatedAt,
    compact_files: {
      instructions: 'alphas/factory/FACTORY_AGENT.md',
      competition: 'alphas/factory/competition-compact.json',
      operators: 'alphas/factory/operators-compact.json',
      cluster_context_pattern: 'alphas/factory/context/<cluster>.json',
      attempt_summary: 'alphas/factory/attempt-summary.json',
      attempt_index_machine_memory: 'alphas/factory/attempt-index.jsonl',
      frontier: 'alphas/factory/master-frontier.json',
      scoreboard: 'alphas/factory/cluster-scoreboard.json',
      batch_summary: 'alphas/factory/active-batch-summary.json',
    },
    authoritative_campaign: source('alphas/research/campaign.json'),
  };
  const competition = {
    schema_version: 1,
    generator_version: GENERATOR_VERSION,
    qualification: { evidence: 'Slow', metric: 'IR', operator: '>', threshold: 0.07 },
    correlation: { evidence: 'Slow PNL', comparison: 'Pearson correlation on aligned daily PNL', direct_compatibility_operator: '<=', threshold: 0.5 },
    quality_override: { multiplier: 1.2, comparison_metric: 'IR/sqrt(turnover)', rule: 'candidate >= multiplier * each correlated predecessor' },
    sequencing_rule: 'A candidate is valid after all predecessors only if directly compatible with each, or it clears the quality override against every correlated predecessor. Submit weaker qualifying values before stronger override successors.',
    evidence_policy: { Fast: 'exploration, screening, PNL-neighborhood discovery, and allocation only', Slow: 'final qualification, correlation compatibility, and sequence evidence' },
    simulator_defaults: { region_universe: 'US:TOP1000', neutralization: 'industry', delay: 0, slippage: false, slippage_value: 0.1, liquidity_universe_simulation: false, note: 'Observed in the current batch scripts; Slow inherits the Fast settings.' },
    inactive_gate_rule: 'Use np.nan, never 0.0, when a stock/day should have no position.',
    invalid_outcomes: ['OS limit exceeded', 'missing metrics object', 'blank IR', 'non-numeric IR', 'empty 0x0 stock book', 'missing daily PNL series', 'insufficient Slow lookback', 'future-data access', 'non-numeric/boolean final signal', 'no usable cross-sectional variation'],
    sources: [source('Trexquant-Alpha-Generation-Competition.md'), source('ALPHA_RESEARCH_AGENT.md'), source('RESEARCH_CANDIDATE_FORMAT.md'), source('scripts/trexsim-research-state.js'), source('scripts/trexsim-api-batch.js')],
  };
  const scoreboard = buildScoreboard(attempts);
  const activeBatch = buildActiveBatch(campaign);
  const attemptSummary = buildAttemptSummary(attempts, campaign, activeBatch);
  return {
    'alphas/factory/FACTORY_AGENT.md': factoryAgent(),
    'alphas/factory/state.json': state,
    'alphas/factory/competition-compact.json': competition,
    'alphas/factory/operators-compact.json': buildOperators(),
    ...buildContexts(),
    'alphas/factory/attempt-index.jsonl': attempts.map(row => JSON.stringify(stable(row))).join('\n') + (attempts.length ? '\n' : ''),
    'alphas/factory/attempt-summary.json': attemptSummary,
    'alphas/factory/master-frontier.json': buildFrontier(),
    'alphas/factory/cluster-scoreboard.json': scoreboard,
    'alphas/factory/active-batch-summary.json': activeBatch,
  };
}

function renderArtifact(value) { return typeof value === 'string' ? value : stringify(value); }
function refresh() {
  const artifacts = buildAll();
  for (const [file, value] of Object.entries(artifacts)) write(file, renderArtifact(value));
  return artifacts;
}

module.exports = { CLUSTERS, FACTORY, GENERATOR_VERSION, ROOT, buildAll, fieldFingerprint, formulaFingerprint, hashFile, operatorFingerprint, refresh, renderArtifact, stable, structuralFingerprint };
