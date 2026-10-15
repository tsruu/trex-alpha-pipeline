'use strict';

// Conservative, source-level checks for the part of TrexSim's Python buffer
// contract that can be checked before a browser submission.  This is not a
// Python parser and deliberately does not try to prove that arbitrary helper
// code is causal.  It catches the common, unambiguous forms of future access:
// negative delay/window literals and negative time-axis indexing.

const NUMBER = '(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?';

const WINDOW_FUNCTIONS = new Set([
  'ts_delay', 'ts_diff', 'ts_mean', 'ts_std', 'ts_zscore', 'ts_rank', 'ts_sum',
  'ts_min', 'ts_max', 'ts_median', 'ts_skew', 'ts_mean_exp', 'ts_norm',
  'ts_corr_binary',
]);

function maskPython(code) {
  // Preserve newlines and offsets while hiding comments and string contents.
  // This keeps the scanner from treating examples inside a comment/string as
  // executable formula code.
  const source = String(code);
  const chars = source.split('');
  let quote = null;
  let triple = false;
  let escaped = false;
  for (let i = 0; i < chars.length; i += 1) {
    const ch = source[i];
    const next = source.slice(i, i + 3);
    if (!quote) {
      if (ch === '#') {
        for (; i < chars.length && source[i] !== '\n'; i += 1) chars[i] = ' ';
        if (i < chars.length) chars[i] = '\n';
        continue;
      }
      if (next === "'''" || next === '"""') {
        quote = ch;
        triple = true;
        chars[i] = chars[i + 1] = chars[i + 2] = ' ';
        i += 2;
        continue;
      }
      if (ch === "'" || ch === '"') {
        quote = ch;
        triple = false;
        chars[i] = ' ';
        continue;
      }
      continue;
    }

    if (triple && source.slice(i, i + 3) === quote.repeat(3)) {
      chars[i] = chars[i + 1] = chars[i + 2] = ' ';
      i += 2;
      quote = null;
      triple = false;
      escaped = false;
      continue;
    }
    if (!triple && !escaped && ch === quote) {
      chars[i] = ' ';
      quote = null;
      continue;
    }
    escaped = !escaped && ch === '\\';
    if (ch !== '\n') chars[i] = ' ';
    if (ch === '\n' && !triple) quote = null;
  }
  return chars.join('');
}

function lineAt(source, offset) {
  return source.slice(0, offset).split('\n').length;
}

function matchingParen(source, open) {
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === '(') depth += 1;
    else if (source[i] === ')' && --depth === 0) return i;
  }
  return -1;
}

function splitArguments(source) {
  const args = [];
  let start = 0;
  let parens = 0;
  let brackets = 0;
  let braces = 0;
  for (let i = 0; i < source.length; i += 1) {
    switch (source[i]) {
      case '(': parens += 1; break;
      case ')': parens -= 1; break;
      case '[': brackets += 1; break;
      case ']': brackets -= 1; break;
      case '{': braces += 1; break;
      case '}': braces -= 1; break;
      case ',':
        if (parens === 0 && brackets === 0 && braces === 0) {
          args.push(source.slice(start, i));
          start = i + 1;
        }
        break;
      default: break;
    }
  }
  if (source.slice(start).trim()) args.push(source.slice(start));
  return args;
}

function isNegativeLiteral(value) {
  const expression = String(value).replace(/\s+/g, '');
  // Permit harmless parenthesization, e.g. -(1), while leaving dynamic forms
  // such as -window to the runtime and human review.
  return new RegExp(`^\\(*-\\(*${NUMBER}\\)*\\)*$`).test(expression);
}

function isUnaryNegative(value) {
  const expression = String(value).replace(/\s+/g, '');
  return /^\(*-/.test(expression);
}

function isNegativeTimeIndex(index) {
  const expression = String(index).replace(/\s+/g, '');
  return new RegExp(`^-\\(*${NUMBER}\\)*$`).test(expression) || /^\(*-[A-Za-z_]\w*/.test(expression);
}

function findCalls(masked, source, functionName) {
  const calls = [];
  const pattern = new RegExp(`\\b${functionName}\\s*\\(`, 'g');
  let match;
  while ((match = pattern.exec(masked))) {
    const open = masked.indexOf('(', match.index);
    const close = matchingParen(masked, open);
    if (close < 0) continue;
    calls.push({
      args: splitArguments(masked.slice(open + 1, close)),
      offset: match.index,
      line: lineAt(source, match.index),
    });
    pattern.lastIndex = close + 1;
  }
  return calls;
}

function findFutureAccessViolations(code) {
  const source = String(code || '');
  const masked = maskPython(source);
  const violations = [];

  for (const functionName of WINDOW_FUNCTIONS) {
    for (const call of findCalls(masked, source, functionName)) {
      const periodIndex = functionName === 'ts_corr_binary' ? 2 : 1;
      const period = call.args[periodIndex];
      if (period !== undefined && (isNegativeLiteral(period) || isUnaryNegative(period))) {
        violations.push({
          line: call.line,
          code: functionName,
          message: `${functionName} has a negative time window/offset; future data is not allowed`,
        });
      }
    }
  }

  // A negative index on the time axis (the second dimension in TrexSim's
  // stock-by-date matrices) selects from the end of the full history and is
  // therefore a future-data escape hatch in a custom helper.
  const timeIndex = /\[\s*[^\],]+\s*,\s*([^\]]+)\]/g;
  let match;
  while ((match = timeIndex.exec(masked))) {
    if (isNegativeTimeIndex(match[1])) {
      violations.push({
        line: lineAt(source, match.index),
        code: 'time-index',
        message: 'negative time-axis indexing is not allowed; use ts_delay or a past-only slice',
      });
    }
  }

  // Catch direct point reads such as x[:, t + 1].  Slice endpoints such as
  // x[:, t + 1] in x[:, t-d+1:t+1] are intentionally not rejected here: the
  // latter is a normal exclusive endpoint and cannot be distinguished safely
  // without a Python AST/type-aware analysis.
  const futurePoint = /\[\s*:\s*,\s*([A-Za-z_]\w*)\s*\+\s*(?:[A-Za-z_]\w*|[1-9]\d*)\s*\]/g;
  while ((match = futurePoint.exec(masked))) {
    violations.push({
      line: lineAt(source, match.index),
      code: 'time-index',
      message: `time-axis point index '${match[1]} + ...' may read future data`,
    });
  }

  return violations;
}

function formatFutureAccessViolations(violations) {
  return violations.map((violation) => `line ${violation.line}: ${violation.message}`);
}

module.exports = { findFutureAccessViolations, formatFutureAccessViolations };
