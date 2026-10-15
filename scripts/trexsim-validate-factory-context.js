#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { ROOT, buildAll, renderArtifact } = require('./trexsim-factory-context');

const expected = buildAll();
const errors = [];
for (const [file, value] of Object.entries(expected)) {
  const target = path.join(ROOT, file);
  if (!fs.existsSync(target)) { errors.push(`${file}: missing`); continue; }
  const actual = fs.readFileSync(target, 'utf8');
  if (actual !== renderArtifact(value)) errors.push(`${file}: stale or non-reproducible`);
  if (file.endsWith('.json')) {
    try { JSON.parse(actual); } catch (error) { errors.push(`${file}: invalid JSON (${error.message})`); }
  }
  if (file.endsWith('.jsonl')) {
    actual.split('\n').filter(Boolean).forEach((line, index) => {
      try { JSON.parse(line); } catch (error) { errors.push(`${file}:${index + 1}: invalid JSON (${error.message})`); }
    });
  }
  if (actual.includes('alphas/research-archive/')) errors.push(`${file}: archived research leaked into compact context`);
}

const attemptsPath = path.join(ROOT, 'alphas/factory/attempt-index.jsonl');
if (fs.existsSync(attemptsPath)) {
  for (const line of fs.readFileSync(attemptsPath, 'utf8').split('\n').filter(Boolean)) {
    const row = JSON.parse(line);
    if (row.location?.kind !== 'live') errors.push(`${row.id}: archived attempt present in active index`);
    const candidatePath = path.join(ROOT, row.location?.candidate || '');
    if (!fs.existsSync(candidatePath)) errors.push(`${row.id}: candidate path does not resolve`);
    else {
      const candidate = JSON.parse(fs.readFileSync(candidatePath, 'utf8'));
      for (const mode of ['fast', 'slow']) {
        const compact = row[mode]?.metrics;
        const detailed = candidate.runs?.[mode]?.result;
        if (compact && (!detailed || compact.ir !== (detailed.ir ?? null) || compact.turnover !== (detailed.turnover ?? null) || compact.ir_sqrt_turnover !== (detailed.ir_tvr ?? null))) {
          errors.push(`${row.id}: ${mode} metric differs from candidate source`);
        }
      }
    }
  }
}

const frontier = JSON.parse(fs.readFileSync(path.join(ROOT, 'alphas/factory/master-frontier.json'), 'utf8'));
const pool = JSON.parse(fs.readFileSync(path.join(ROOT, 'alphas/research/legacy-optimal-pool.json'), 'utf8'));
for (const row of frontier.legacy_selected_baseline) {
  const source = pool.submission_order.find(item => String(item.id) === row.id);
  if (!source) errors.push(`${row.id}: frontier ID absent from legacy source`);
  else if (row.slow_ir !== source.ir || row.turnover !== source.tvr || row.ir_sqrt_turnover !== source.ir_tvr) errors.push(`${row.id}: frontier metric differs from legacy source`);
  if (row.pnl_reference && !fs.existsSync(path.join(ROOT, row.pnl_reference))) errors.push(`${row.id}: PNL reference does not resolve`);
}

const markdown = fs.readFileSync(path.join(ROOT, 'alphas/factory/FACTORY_AGENT.md'), 'utf8');
const words = markdown.trim().split(/\s+/).length;
if (words >= 2500) errors.push(`FACTORY_AGENT.md: ${words} words (must be under 2500)`);
if (!markdown.startsWith('# ')) errors.push('FACTORY_AGENT.md: missing Markdown heading');

const contexts = JSON.parse(fs.readFileSync(path.join(ROOT, 'data-distribution.json'), 'utf8')).items;
const knownFields = new Set(contexts.map(item => item.varname));
for (const file of fs.readdirSync(path.join(ROOT, 'alphas/factory/context')).filter(name => name.endsWith('.json'))) {
  const context = JSON.parse(fs.readFileSync(path.join(ROOT, 'alphas/factory/context', file), 'utf8'));
  for (const field of [...context.permitted_primary_fields, ...context.permitted_cross_cluster_external_fields]) {
    if (!knownFields.has(field.name || field.field)) errors.push(`${file}: unknown permitted field ${field.name || field.field}`);
  }
}

if (errors.length) {
  process.stderr.write(`${errors.join('\n')}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`Factory context valid: ${Object.keys(expected).length} artifacts, ${words} instruction words.\n`);
}
