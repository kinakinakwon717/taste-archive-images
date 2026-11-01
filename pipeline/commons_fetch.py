import json, subprocess, sys, urllib.parse, os, re
# 사용법: python3 commons_fetch.py 저장폴더 "key=검색어" ...   (CC0·퍼블릭도메인 사진만, 키당 최대 6장)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
BAD = re.compile(r'painting|lithograph|engraving|postcard|map|drawing|illustration|print|stereo|\b1[0-8]\d\d\b|19[0-6]\d|aerial view from|logo|svg', re.I)
UA = 'TasteArchiveShorts/1.0 (kinakwon0717@gmail.com)'
meta = {}
for arg in sys.argv[2:]:
    key, q = arg.split('=', 1)
    url = ('https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6'
           '&gsrsearch=' + urllib.parse.quote(q + ' filetype:bitmap') + '&gsrlimit=40&prop=imageinfo'
           '&iiprop=url|size|extmetadata&iiurlwidth=1600')
    raw = subprocess.run(['curl', '-s', '-m', '40', '-A', UA, url], capture_output=True, text=True).stdout
    try: pages = json.loads(raw).get('query', {}).get('pages', {}).values()
    except Exception: print(key, 'FAIL'); continue
    n = 0
    for p in sorted(pages, key=lambda p: p.get('index', 99)):
        ii = p['imageinfo'][0]; m = ii.get('extmetadata', {})
        lic = m.get('LicenseShortName', {}).get('value', '')
        if lic not in ('CC0', 'Public domain') or ii['width'] < 1500 or BAD.search(p['title']):
            continue
        fn = f'{out}/{key}_{n}.jpg'
        subprocess.run(['curl', '-s', '-m', '60', '-A', UA, '-o', fn, ii['thumburl']])
        meta[f'{key}_{n}'] = {'title': p['title'], 'license': lic, 'page': ii.get('descriptionurl'), 'size': [ii['width'], ii['height']]}
        n += 1
        if n >= 6: break
    print(key, n)
json.dump(meta, open(f'{out}/meta.json', 'w'), ensure_ascii=False, indent=1)
