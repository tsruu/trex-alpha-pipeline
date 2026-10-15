#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const n = process.argv[2];
if (!n) { console.error('Usage: node trexsim-paste-code.js <alphaNum>'); process.exit(1); }
const nn = String(n).padStart(2, '0');
const file = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
const content = fs.readFileSync(file, 'utf8');
const m = content.match(/### v1\s*\n\n```python\n([\s\S]*?)\n```/);
if (!m) { console.error('No v1 code found'); process.exit(1); }
const code = m[1];
const escaped = code.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
const expr = `(() => { const code = \`${escaped}\`; const root = document.querySelector('react-app')?.shadowRoot; const view = root?.querySelector('.cm-content')?.cmTile?.view; if (!view) return {error:'no view'}; view.dispatch({changes:{from:0,to:view.state.doc.length,insert:code}}); const doc=view.state.doc.toString(); return {ok:true, len:doc.length, hasAlpha:doc.includes('alpha ='), tail:doc.slice(-30)}; })()`;
process.stdout.write(expr);
