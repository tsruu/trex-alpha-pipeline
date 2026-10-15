#!/usr/bin/env node
// Output raw v1 python code for alpha N (for embedding in CDP)
const fs = require('fs');
const path = require('path');
const n = process.argv[2];
const nn = String(n).padStart(2, '0');
const file = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
const content = fs.readFileSync(file, 'utf8');
const m = content.match(/### v1\s*\n\n```python\n([\s\S]*?)\n```/);
if (!m) process.exit(1);
process.stdout.write(m[1]);
