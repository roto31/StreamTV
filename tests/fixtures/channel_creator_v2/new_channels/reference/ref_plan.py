#!/usr/bin/env python3
"""Reference planner + compiler for NEW StreamTV channels in the style of channels 1224/1225/101/214/401/704/1031/1128.
Input: candidates_<n>.json ({channel: spec, candidates: [...]}) — candidates in stream order (programs first, then breaks).
Output: channel-<n>-<slug>.yaml and <n>.yml, byte-identical to the delivered channels."""
import json, sys, pathlib, yaml

def dur(s):
    s = int(s); h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return ('PT' + (f'{h}H' if h else '') + (f'{m}M' if m else '') + (f'{sec}S' if sec else '')) if s else 'PT1S'
def short(net): return net.split(' /')[0].split(' (')[0]

STYLE = {  # field order and text templates; 'prime_2026' is the default for new channels
  'kids_2026':  dict(date_before_slot=False, slot_without_date='{title} ({net})',
                     break_notes='Commercial/bumper break reel. Page: {page}', id_notes='Station holiday promo / ID. Page: {page}'),
  'prime_2026': dict(date_before_slot=True, slot_without_date='{title} ({net}, {year})',
                     break_notes='Commercial break reel. Page: {page}', id_notes='Station holiday promo / ID. Page: {page}'),
}

def compile_streams(spec, cands):
    st, P = STYLE[spec['style']], spec['collection_prefix']; out = []
    for c in cands:
        sid = c['id']
        if c['role'] in ('program', 'marathon'):
            slot = f"{c['title']} ({c['network']}, {c['date']})" if c['date'] else st['slot_without_date'].format(title=c['title'], net=c['network'], year=c['year'])
            s = {'id': sid, 'collection': f"{P} - {c['title']} ({short(c['network'])} {c['year']}) [{sid}]", 'type': 'event', 'year': c['year']}
            if st['date_before_slot']: s['broadcast_date'] = c['date']
            s.update(slot=slot, network=c['network'], runtime=dur(c['seconds']), source=c['source'], url=c['url'],
                     notes=f"Tier {c['tier']}; commercials: {c['commercials']}. {c['note']} Page: {c['page']}")
            if not st['date_before_slot'] and c['date']: s['broadcast_date'] = c['date']
        else:
            tmpl = st['id_notes'] if c['role'] == 'station_id' else st['break_notes']
            s = {'id': sid, 'collection': f"{P} - Break - {c['title']} [{sid}]", 'type': 'commercial', 'slot': c['title'],
                 'network': c['network'], 'runtime': dur(c['seconds']), 'source': c['source'], 'url': c['url'], 'notes': tmpl.format(page=c['page'])}
            if c['date']: s['broadcast_date'] = c['date']; s['year'] = int(c['date'][:4])
        c['_slot'], c['_coll'] = s['slot'], s['collection']; out.append(s)
    return out

def plan(spec, cands):
    progs = [c for c in cands if c['role'] == 'program']
    marathons = [c for c in cands if c['role'] == 'marathon']
    ids = [c for c in cands if c['role'] == 'station_id']
    brk = [c for c in cands if c['role'] == 'break']
    longs = [c for c in brk if c['seconds'] > spec['long_reel_seconds']]
    groups = {g: [c for c in brk if c['group'] == g and c not in longs] for g in spec['break_groups']}
    order = sorted(progs, key=lambda c: c['date'] or f"{c['year']}-12-31")          # stable: ties keep input order
    gaps = [[] for _ in order]
    if spec['rotation'] == 'parity_alternate':                                        # channel 1225 (first build)
        a, b = (groups[g] for g in spec['break_groups']); ia = ib = 0
        for i in range(len(order)):
            if i % 2 == 0: gaps[i].append(a[ia % len(a)]); ia += 1
            else: gaps[i].append(b[ib % len(b)]); ib += 1
    else:                                                                             # interleave_wrap (all later builds)
        rot = []
        for k in range(max(len(v) for v in groups.values())):
            for g in spec['break_groups']:
                if k < len(groups[g]): rot.append(groups[g][k])
        if rot:
            for k in range(max(len(order), len(rot))): gaps[k % len(order)].append(rot[k % len(rot)])
    items = []
    for i, (p, g) in enumerate(zip(order, gaps)):
        items.append({'all': p['id'], 'custom_title': p['_slot']})
        for b in g: items.append({'all': b['id'], 'custom_title': 'Station Break: ' + b['title'], 'filler_kind': 'Commercial'})
        if spec['station_id_after_each_gap'] and ids:
            pr = ids[i % len(ids)]; items.append({'all': pr['id'], 'custom_title': 'Station ID: ' + pr['title'], 'filler_kind': 'Commercial'})
    for b in longs: items.append({'all': b['id'], 'custom_title': 'Commercial Break Marathon: ' + b['title'], 'filler_kind': 'Commercial'})
    for p in marathons: items.append({'all': p['id'], 'custom_title': p['_slot']})
    content = [{'key': c['id'], 'collection': c['_coll'], 'order': 'chronological'} for c in cands if c['role'] in ('program', 'marathon')]
    content += [{'key': c['id'], 'collection': c['_coll'], 'order': 'chronological'} for g in spec['break_groups'] for c in groups[g]]
    content += [{'key': c['id'], 'collection': c['_coll'], 'order': 'chronological'} for c in longs + ids]
    key = spec['sequence_key']
    return {'name': f"{spec['number']} {spec['name']}", 'description': spec['schedule_description'],
            'media': {'preferred_extension': 'mp4', 'mp4_only': True}, 'content': content,
            'sequence': [{'key': key, 'items': items}], 'playout': [{'sequence': key}, {'repeat': True}]}

def build(path, outdir):
    d = json.load(open(path)); spec, cands = d['channel'], d['candidates']
    streams = compile_streams(spec, cands)
    chan = {'channels': [{'number': spec['number'], 'name': spec['name'], 'group': spec['group'], 'description': spec['description'],
                          'enabled': True, 'streams': streams}]}
    outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    cf, sf = outdir/f"channel-{spec['number']}-{spec['slug']}.yaml", outdir/f"{spec['number']}.yml"
    yaml.safe_dump(chan, open(cf, 'w'), sort_keys=False, allow_unicode=True, width=200)
    yaml.safe_dump(plan(spec, cands), open(sf, 'w'), sort_keys=False, allow_unicode=True, width=200)
    return cf, sf

if __name__ == '__main__':
    for p in sys.argv[2:]: print(*build(p, sys.argv[1]))
