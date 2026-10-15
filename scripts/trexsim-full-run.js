#!/usr/bin/env node
// Outputs CDP expression: wait view, paste code, click Run, wait for metrics, return all
const fs = require('fs');
const path = require('path');
const n = process.argv[2];
if (!n) { console.error('Usage: node trexsim-full-run.js <alphaNum>'); process.exit(1); }
const nn = String(n).padStart(2, '0');
const file = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
const content = fs.readFileSync(file, 'utf8');
const m = content.match(/### v1\s*\n\n```python\n([\s\S]*?)\n```/);
if (!m) { console.error('No v1 code'); process.exit(1); }
const code = m[1].replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
const expr = `new Promise(async resolve => {
  const waitView = () => new Promise(r => {
    const c = () => {
      const v = document.querySelector('react-app')?.shadowRoot?.querySelector('.cm-content')?.cmTile?.view;
      if (v) r(v); else setTimeout(c, 500);
    }; c();
  });
  const root = () => document.querySelector('react-app')?.shadowRoot || document;
  try {
    const view = await waitView();
    const code = \`${code}\`;
    view.dispatch({changes:{from:0,to:view.state.doc.length,insert:code}});
    const runBtn = [...root().querySelectorAll('button')].find(b => b.textContent.includes('Run Simulation'));
    if (!runBtn) return resolve({error:'no run button', hasAlpha: view.state.doc.toString().includes('alpha =')});
    runBtn.click();
    let n = 0;
    const waitDone = () => new Promise(r => {
      const check = () => {
        const url = location.href;
        const hasId = /\\/alpha\\/\\d+/.test(url);
        const btns = [...root().querySelectorAll('button')];
        const cancel = btns.some(b => b.textContent.includes('Cancel'));
        const hasIR = btns.some(b => b.textContent.trim() === 'IR');
        if (hasId && !cancel && hasIR) {
          const t = root().textContent || '';
          const get = (re) => { const m = t.match(re); return m ? m[1] : null; };
          const wm = t.match(/(\\d{4}-\\d{2}-\\d{2})\\s*[—-]\\s*(\\d{4}-\\d{2}-\\d{2})/);
          r({
            done: true,
            url,
            id: url.split('/').filter(Boolean).pop(),
            window: wm ? wm[0] : null,
            IR: get(/IR\\s*([\\d.-]+)/),
            TVR: get(/TVR\\s*([\\d.-]+)/),
            DD: get(/DD\\s*([\\d.-]+)/),
            Ret: get(/Ret\\s*([\\d.-]+)/),
            IRSqrt: get(/IR\\/sqrt\\(TVR\\)\\s*([\\d.-]+)/),
            Booksize: get(/Booksize\\s*([\\d.x]+)/),
            NumStks: get(/NumStks\\s*([\\d.x]+)/),
            Liq: get(/Liq\\s*(\\d+)/),
            LiqN: get(/LiqN\\s*(\\d+)/),
            Region: get(/Region\\s*(us)/),
            errorText: t.includes('Error') ? t.slice(t.indexOf('Error'), t.indexOf('Error')+200) : null
          });
        } else if (n > 50) {
          r({done:false, url, cancel, hasId, hasIR, n});
        } else { n++; setTimeout(check, 2000); }
      };
      check();
    });
    resolve(await waitDone());
  } catch (e) {
    resolve({error: String(e)});
  }
})`;
process.stdout.write(expr);
