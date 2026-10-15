#!/usr/bin/env node
// Outputs CDP expression to extract metrics from shadow DOM
process.stdout.write(`(() => {
  const t = document.querySelector('react-app')?.shadowRoot?.textContent || '';
  const get = (re) => { const m = t.match(re); return m ? m[1] : null; };
  const wm = t.match(/(\\d{4}-\\d{2}-\\d{2})\\s*[—-]\\s*(\\d{4}-\\d{2}-\\d{2})/);
  return {
    url: location.href,
    id: location.pathname.split('/').filter(Boolean).pop(),
    window: wm ? wm[0].replace(/-/g, (m, o) => o > 10 ? '—' : '-') : null,
    IR: get(/IR\\s*([\\d.-]+)/),
    TVR: get(/TVR\\s*([\\d.-]+)/),
    DD: get(/DD\\s*([\\d.-]+)/),
    Ret: get(/Ret\\s*([\\d.-]+)/),
    IRSqrt: get(/IR\\/sqrt\\(TVR\\)\\s*([\\d.-]+)/),
    Booksize: get(/Booksize\\s*([\\d.x]+)/),
    NumStks: get(/NumStks\\s*([\\d.x]+)/),
    Liq: get(/Liq\\s*(\\d+)/),
    LiqN: get(/LiqN\\s*(\\d+)/),
    Region: get(/Region\\s*(us)/)
  };
})()`);
