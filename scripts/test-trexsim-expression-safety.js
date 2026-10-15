#!/usr/bin/env node

const assert = require('assert');
const {
  findFutureAccessViolations,
  formatFutureAccessViolations,
} = require('./trexsim-expression-safety');

function messages(code) {
  return formatFutureAccessViolations(findFutureAccessViolations(code));
}

assert.deepStrictEqual(messages('alpha = ts_delay(close, 1)'), []);
assert.deepStrictEqual(messages('alpha = ts_corr_binary(close, volume, 20)'), []);
assert.deepStrictEqual(messages('# ts_delay(close, -1)\nalpha = close'), []);
assert.deepStrictEqual(messages("alpha = 'ts_delay(close, -1)'"), []);

assert.match(messages('alpha = ts_delay(close, -1)')[0], /line 1: ts_delay/);
assert.match(messages('alpha = ts_delay(close, -(1))')[0], /negative time window/);
assert.match(messages('alpha = ts_delay(close, -window)')[0], /negative time window/);
assert.match(messages('alpha = ts_corr_binary(close, volume, -3)')[0], /ts_corr_binary/);
assert.match(messages('alpha = ts_mean(close, -2.0)')[0], /ts_mean/);
assert.match(messages('def helper(x):\n    return x[:, -1]\nalpha = helper(close)')[0], /negative time-axis/);
assert.match(messages('def helper(x):\n    return x[:, -dt]\nalpha = helper(close)')[0], /negative time-axis/);
assert.match(messages('def helper(x):\n    return x[:, t + 1]\nalpha = helper(close)')[0], /may read future data/);
assert.match(messages('def helper(x):\n    return x[:, t + dt]\nalpha = helper(close)')[0], /may read future data/);
assert.deepStrictEqual(messages('def helper(x, d):\n    return ts_delay(x, d)\nalpha = helper(close, window)'), []);
assert.deepStrictEqual(messages('def helper(x, t, d):\n    return x[:, t-d+1:t+1]\nalpha = helper(close, t, d)'), []);

console.log('expression safety checks passed');
