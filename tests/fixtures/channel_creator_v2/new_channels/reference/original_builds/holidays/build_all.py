#!/usr/bin/env python3
"""Build StreamTV channel + schedule YAML, urls.tsv and SOURCES.md for the six holiday channels."""
import json, urllib.parse, yaml, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from holidays_data import CHANNELS
from holidays_extras import EXTRAS, TERMS

H = pathlib.Path('/home/claude/holidays')
A = json.load(open(H/'archive.json')); YT = json.load(open(H/'yt.json'))
OUT = H/'out'
for d in ('channels', 'schedules', 'sources', 'urls'): (OUT/d).mkdir(parents=True, exist_ok=True)

def dur(s):
    s = int(s); h, m, sec = s//3600, (s % 3600)//60, s % 60
    return ('PT'+(f'{h}H' if h else '')+(f'{m}M' if m else '')+(f'{sec}S' if sec else '')) if s else 'PT1S'

def resolve(ref):
    """-> (url, seconds, source, page_url, owner_md)"""
    if ref[0] == 'a':
        it = A[ref[1]]; files = it['f']
        f = next(x for x in files if x[0] == ref[2]) if ref[2] else files[0]
        url = 'https://archive.org/download/%s/%s' % (ref[1], urllib.parse.quote(f[0]))
        u = it.get('u')
        own = f'[@{u}](https://archive.org/details/@{u})' if u else 'uploader not shown'
        return url, f[1], 'archive', f'https://archive.org/details/{ref[1]}', own
    secs, play, handle = YT[ref[1]][:3]
    url = 'https://www.youtube.com/watch?v=' + ref[1]
    own = f'[{handle}](https://www.youtube.com/{handle})' if handle else ''
    return url, secs, 'youtube', url, own

ADS = {'yes': 'Yes — stated in description/title', 'mostly': 'Mostly — stated', 'some': 'Some — stated (partly cut)',
       'label-only': 'Likely — only the "WOC" label in the title', 'unverified': 'Not verified — description silent',
       'inferred': 'Inferred from runtime only', 'no': 'No — removed or never present'}

def fmt(secs, title):
    if 'Parade' in title and secs >= 90*60: return f'Parade broadcast (about {round(secs/3600,1):g} h)'
    if 'tape' in title.lower() or ' + ' in title or secs > 100*60: return 'Broadcast block (several programs or long event)'
    if secs >= 45*60: return 'Full-length special (~60 min)'
    if secs >= 18*60: return 'Half-hour special'
    return 'Partial / excerpt'

def netshort(n): return n.split(' /')[0].split(' (')[0]

summary = []
for ch in CHANNELS:
    num, slug, name, prefix = ch['number'], ch['slug'], ch['name'], ch['name']
    streams, progs, br = [], [], {'mn': [], 'net': [], 'long': []}
    for sid, title, net, date, year, tier, ads, ref, note in ch['programs']:
        url, secs, src, page, own = resolve(ref)
        coll = f'{prefix} - {title} ({netshort(net)} {year}) [{sid}]'
        slot = f'{title} ({net}{", "+date if date else ""})'
        s = {'id': sid, 'collection': coll, 'type': 'event', 'year': year, 'slot': slot, 'network': net,
             'runtime': dur(secs), 'source': src, 'url': url,
             'notes': f'Tier {tier}; commercials: {ads}. {note} Page: {page}'}
        if date: s['broadcast_date'] = date
        streams.append(s)
        progs.append(dict(sid=sid, coll=coll, slot=slot, sort=date or f'{year}-12-31', title=title, net=net, date=date,
                          year=year, tier=tier, ads=ads, secs=secs, src=src, page=page, own=own, note=note))
    for grp in ('mn', 'net'):
        for sid, title, net, date, ref in ch[grp]:
            url, secs, src, page, own = resolve(ref)
            coll = f'{prefix} - Break - {title} [{sid}]'
            s = {'id': sid, 'collection': coll, 'type': 'commercial', 'slot': title, 'network': net, 'runtime': dur(secs),
                 'source': src, 'url': url, 'notes': 'Commercial/bumper break reel. Page: ' + page}
            if date: s['broadcast_date'] = date; s['year'] = int(date[:4])
            streams.append(s)
            rec = dict(sid=sid, coll=coll, title=title, net=net, date=date, secs=secs, src=src, page=page, own=own, grp=grp)
            br['long' if secs > 20*60 else grp].append(rec)

    chan = {'channels': [{'number': num, 'name': name, 'group': 'Holiday', 'description': ch['desc'],
                          'enabled': True, 'streams': streams}]}
    cfile = OUT/'channels'/f'channel-{num}-{slug}.yaml'
    yaml.safe_dump(chan, open(cfile, 'w'), sort_keys=False, allow_unicode=True, width=200)

    # ---- schedule
    content = [{'key': p['sid'], 'collection': p['coll'], 'order': 'chronological'} for p in progs]
    content += [{'key': b['sid'], 'collection': b['coll'], 'order': 'chronological'} for g in ('mn', 'net', 'long') for b in br[g]]
    regular = sorted([p for p in progs if not p['sid'].startswith('marathon_')], key=lambda p: p['sort'])
    marathon = [p for p in progs if p['sid'].startswith('marathon_')]
    mn, nt = br['mn'], br['net']
    # interleave Minnesota and network reels, then give each gap one reel; if there are more
    # reels than programs, the extra reels double up so every reel is used each loop
    order_b = []
    for k in range(max(len(mn), len(nt))):
        if k < len(mn): order_b.append(mn[k])
        if k < len(nt): order_b.append(nt[k])
    gaps = [[] for _ in regular]
    n = max(len(regular), len(order_b))
    for k in range(n): gaps[k % len(regular)].append(order_b[k % len(order_b)])
    items = []
    for p, gb in zip(regular, gaps):
        items.append({'all': p['sid'], 'custom_title': p['slot']})
        for b in gb:
            items.append({'all': b['sid'], 'custom_title': 'Station Break: ' + b['title'], 'filler_kind': 'Commercial'})
    for b in br['long']:
        items.append({'all': b['sid'], 'custom_title': 'Commercial Break Marathon: ' + b['title'], 'filler_kind': 'Commercial'})
    for p in marathon:
        items.append({'all': p['sid'], 'custom_title': p['slot']})
    key = f'{slug}-channel'
    y0, y1 = regular[0]['sort'][:4], regular[-1]['sort'][:4]
    mnlabel = ' (alternating Minnesota and network reels)' if mn else ''
    sched = {'name': f'{num} {name}',
             'description': f'Chronological run ({y0} -> {y1}) of off-air {name.replace("Vintage ","")} broadcasts; one vintage station-break reel{mnlabel} between programs, then long commercial reels and mixed tapes. Loops.',
             'media': {'preferred_extension': 'mp4', 'mp4_only': True}, 'content': content,
             'sequence': [{'key': key, 'items': items}], 'playout': [{'sequence': key}, {'repeat': True}]}
    sfile = OUT/'schedules'/f'{num}.yml'
    yaml.safe_dump(sched, open(sfile, 'w'), sort_keys=False, allow_unicode=True, width=200)

    with open(OUT/'urls'/f'{num}-{slug}.tsv', 'w') as f:
        f.write('id\ttype\tnetwork\tdate\truntime\turl\n')
        for s in streams: f.write(f"{s['id']}\t{s['type']}\t{s['network']}\t{s.get('broadcast_date','')}\t{s['runtime']}\t{s['url']}\n")

    # ---- SOURCES.md
    X = EXTRAS[num]
    hdr = '| Program | Platform | Network / station | Air date | Commercials & IDs | Format | Links (item · uploader) | Notes |\n|---|---|---|---|---|---|---|---|'
    def prow(p):
        plat = 'archive.org' if p['src'] == 'archive' else 'YouTube'
        return f"| {p['title']} | {plat} | {p['net']} | {p['date'] or p['year']} | {ADS[p['ads']]} | {fmt(p['secs'], p['title'])} | [item]({p['page']}) · {p['own']} | {p['note']} |"
    def brows(L):
        if not L: return '_None found._'
        rows = [f"| {b['title']} | {'archive.org' if b['src']=='archive' else 'YouTube'} | {b['net']} | {b['date'] or 'not stated'} | {round(b['secs']/60)} min | [item]({b['page']}) · {b['own']} |" for b in L]
        return '| Break reel | Platform | Station | Date | Length | Links |\n|---|---|---|---|---|---|\n' + '\n'.join(rows)
    sections = X.get('program_sections') or [('', lambda p: True)]
    md = [f'# {name} — StreamTV channel {num}: sources', '',
          'Researched November 18, 2026 on archive.org and YouTube. Every row links to the page its facts came from.', '',
          X['intro'], '', '## Plain-language terms', '', TERMS.replace('{{HOLIDAY}}', X['holiday']), '']
    for tier in (1, 2):
        tp = sorted([p for p in progs if p['tier'] == tier], key=lambda p: p['sort'])
        md += [f"## Tier {tier} — {'high-confidence' if tier==1 else 'partial'} matches ({len(tp)})", '']
        if not tp: md += ['_None._', '']; continue
        for label, pred in sections:
            sp = [p for p in tp if pred(p)]
            if not sp: continue
            if label: md += [f'### {label} ({len(sp)})', '']
            md += [hdr] + [prow(p) for p in sp] + ['']
    md += ['## Station-break reels used between programs', '',
           'The channel plays one real break reel between programs' + (', alternating Minnesota and network reels,' if mn else '') +
           ' so the gaps sound like TV from the era. Reels longer than 20 minutes play as a block at the end of each loop.', '',
           '### Minnesota (WCCO 4, KSTP 5, KARE 11)', '', brows([b for b in br['mn']] + [b for b in br['long'] if b['grp']=='mn']), '',
           '### Other stations and networks', '', brows([b for b in br['net']] + [b for b in br['long'] if b['grp']=='net']), '',
           '## Collections and channels worth following', '',
           '| Collection / channel | Platform | Why it matters | Link |', '|---|---|---|---|']
    md += [f'| {a} | {b} | {c} | {d} |' for a, b, c, d in X['collections']] + ['']
    if X.get('also'): md += ['## Also found, not loaded into the channel', ''] + [f'- {x}' for x in X['also']] + ['']
    md += ['## Search gaps and items that could not be verified', ''] + [f'- {x}' for x in X['gaps']] + ['']
    open(OUT/'sources'/f'{num}-{slug}-SOURCES.md', 'w').write('\n'.join(md))
    t1 = sum(p['tier'] == 1 for p in progs)
    nb = sum(len(v) for v in br.values())
    hrs = (sum(p['secs'] for p in progs) + sum(b['secs'] for v in br.values() for b in v)) / 3600
    summary.append((num, name, len(progs), t1, nb, round(hrs, 1)))
    print(f'{num} {name}: {len(progs)} programs ({t1} tier 1), {nb} break reels, {hrs:.1f} h per loop')
json.dump(summary, open(OUT/'summary.json', 'w'))
