import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,pickle,textwrap,re
lib=pickle.load(open(_os.path.join(_WORK,'library.pkl'),'rb'))
UNIT='''def _unit(x):
    x = cs_indneut(x, industry)
    g = np.nansum(np.abs(x), axis=0)
    x = np.where(g > 0, x / np.where(g > 0, g, 1.0), np.nan)
    return at_nan2zero(x)
'''
def body(name):
    code=lib[name]['code'].replace('\t','    ')
    if not re.search(r'^alpha\s*=',code,re.M): raise ValueError(name+' has no alpha =')
    return textwrap.indent(code.rstrip()+'\nreturn alpha','    ')
def composite(names,pos_w,label=''):
    parts=[f'# packed composite {label}: '+' + '.join(names), UNIT]
    for i,n in enumerate(names):
        parts.append(f'def _c{i}():\n    # {n}\n'+body(n)+'\n')
    s=' + '.join(f'{w:.6g} * _unit(_c{i}())' for i,w in enumerate(pos_w))
    parts.append(f'alpha = {s}\nalpha = np.where(alpha == 0, np.nan, alpha)')
    return '\n'.join(parts)
if __name__=='__main__':
    P=json.load(open(_os.path.join(_WORK,'packed.json')))
    c=composite(P[0]['components'],P[0]['pos_w'],'t0'); print(c[:3000]); compile(c,'x','exec'); print('compiles')

UNIT2='''def _unit(x):
    g = industry
    y = np.full(x.shape, np.nan)
    for c in np.unique(g[np.isfinite(g)]):
        m = g == c
        med = np.nanmedian(np.where(m, x, np.nan), axis=0)
        y = np.where(m, x - med[None, :], y)
    pos = np.where(y > 0, y, 0.0); neg = np.where(y < 0, -y, 0.0)
    sp = np.nansum(pos, axis=0); sn = np.nansum(neg, axis=0)
    z = np.where(y > 0, y / np.where(sp > 0, sp, 1.0), np.where(y < 0, y / np.where(sn > 0, sn, 1.0), 0.0))
    return at_nan2zero(np.where(np.isfinite(y), z, np.nan)) * 0.5
'''
def composite2(names,pos_w,label=''):
    return composite(names,pos_w,label).replace(UNIT,UNIT2)

import re as _re
_DV=set(x['varname'] for x in json.load(open(_os.path.join(_REPO,'data-distribution.json')))['items']) if 'json' in dir() else None
def _datavars(code):
    import json as _j
    dv=set(x['varname'] for x in _j.load(open(_os.path.join(_REPO,'data-distribution.json')))['items'])
    return sorted(set(_re.findall(r'\b[a-z_][a-z0-9_]*\b',code)) & dv)
SLICE='''def _win(L):
    T = close.shape[1]
    return None if T > 1500 else max(1, T - L)
def _pad(a, full):
    if a.shape[1] == full.shape[1]:
        return a
    out = np.full(full.shape, np.nan)
    out[:, -a.shape[1]:] = a
    return out
'''
def composite3(names,pos_w,label='',unit=None,margin=5):
    """Like composite(), but in Slow each component only sees its own lookback window (Fast unchanged)."""
    unit=unit or UNIT
    parts=[f'# packed composite {label}: '+' + '.join(names), unit, SLICE]
    calls=[]
    for i,n in enumerate(names):
        code=lib[n]['code']; dv=_datavars(code); L=lib[n]['lookback']+margin
        args=', '.join(dv)
        parts.append(f'def _c{i}({args}):\n    # {n}\n'+body(n)+'\n')
        sl=', '.join(f'{v}[:, _s{i}:]' for v in dv)
        calls.append((i,dv,L))
    lines=[]
    for i,dv,L in calls:
        lines.append(f'_s{i} = _win({L})')
        lines.append(f'_a{i} = _c{i}(' + ', '.join(f'{v}' if True else '' for v in dv).replace(', ',', ') + ')' if False else
                     f'_a{i} = _pad(_c{i}(' + ', '.join(f'({v} if _s{i} is None else {v}[:, _s{i}:])' for v in dv) + '), close)')
    s=' + '.join(f'{w:.6g} * _unit(_a{i})' for i,w in enumerate(pos_w))
    parts.append('\n'.join(lines)+f'\nalpha = {s}\nalpha = np.where(alpha == 0, np.nan, alpha)')
    return '\n'.join(parts)
