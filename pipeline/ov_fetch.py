import json, subprocess, sys, urllib.parse, os, re
# python3 ov_fetch.py 저장폴더 n "key=검색어" ...  Openverse CC0/PDM 사진만
out = sys.argv[1]; per = int(sys.argv[2]); os.makedirs(out, exist_ok=True)
BAD = re.compile(r'painting|lithograph|engraving|postcard|map|drawing|illustration|print|stereo|logo|svg|poster', re.I)
mp = f'{out}/meta.json'
meta = json.load(open(mp)) if os.path.exists(mp) else {}
for arg in sys.argv[3:]:
    key, q = arg.split('=', 1)
    url = ('https://api.openverse.org/v1/images/?license=cc0,pdm&category=photograph&size=large&page_size=20&q='
           + urllib.parse.quote(q))
    raw = subprocess.run(['curl', '-s', '-m', '40', url], capture_output=True, text=True).stdout
    try: res = json.loads(raw)['results']
    except Exception: print(key, 'FAIL', raw[:120]); continue
    n = 0
    for r in res:
        if BAD.search(r.get('title') or '') or (r.get('width') or 0) < 1400: continue
        fn = f'{out}/{key}_{n}.jpg'
        rc = subprocess.run(['curl', '-sL', '-m', '60', '-o', fn, '-w', '%{http_code}', r['url']], capture_output=True, text=True).stdout
        if rc != '200' or os.path.getsize(fn) < 50000:
            os.remove(fn) if os.path.exists(fn) else None; continue
        meta[f'{key}_{n}'] = {'title': r.get('title'), 'license': r.get('license'), 'source': r.get('source'),
                              'creator': r.get('creator'), 'page': r.get('foreign_landing_url'), 'size': [r.get('width'), r.get('height')]}
        n += 1
        if n >= per: break
    print(key, n, flush=True)
    json.dump(meta, open(mp, 'w'), ensure_ascii=False, indent=1)
