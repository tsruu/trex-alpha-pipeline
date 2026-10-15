#!/usr/bin/env node
// CDP expression: wait view, paste code only (no run click)
const fs = require('fs');
const path = require('path');
const n = process.argv[2];
const nn = String(n).padStart(2, '0');
const file = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
const content = fs.readFileSync(file, 'utf8');
const m = content.match(/### v1\s*\n\n```python\n([\s\S]*?)\n```/);
if (!m) process.exit(1);
const code = m[1].replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
process.stdout.write(`new Promise(async r => {
  const wait=()=>new Promise(x=>{const c=()=>{const v=document.querySelector('react-app')?.shadowRoot?.querySelector('.cm-content')?.cmTile?.view; if(v)x(v); else setTimeout(c,500);}; c();});
  const view=await wait();
  const code=\`${code}\`;
  view.dispatch({changes:{from:0,to:view.state.doc.length,insert:code}});
  r({ok:true, hasAlpha:view.state.doc.toString().includes('alpha =')});
})`);
