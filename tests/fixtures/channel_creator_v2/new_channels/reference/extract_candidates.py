#!/usr/bin/env python3
"""Turn the recorded build inputs of the earlier new channels (1224, 1225, 101, 214, 401, 704, 1031, 1128)
into planner input files (candidates_<n>.json). Runs each original build script with runpy in a scratch copy
so nothing in the original folders changes."""
import json, runpy, shutil, sys, pathlib, tempfile, yaml
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'fixtures'); OUT.mkdir(parents=True, exist_ok=True)
H = pathlib.Path('/home/claude')
_dump = yaml.safe_dump
def run(script, cwd):
    sys.path.insert(0, str(cwd)); g = runpy.run_path(str(script), run_name='__build__'); sys.path.pop(0); return g
def short(net): return net.split(' /')[0].split(' (')[0]
def save(n, spec, cands):
    json.dump({'channel': spec, 'candidates': cands}, open(OUT/f'candidates_{n}.json', 'w'), indent=1, ensure_ascii=False)
    print(n, len(cands), 'candidates')

# ---------- 1224 (scratch copy; build writes to its own out/)
tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(H/'primetime', tmp/'pt', ignore=shutil.ignore_patterns('out*', 'pkg*', '*.zip'))
g = run(tmp/'pt'/'build_prime.py', tmp/'pt')
c = []
for sid, title, net, date, year, tier, ads, ref, note in g['PROGRAMS']:
    url, secs, src, page, own = g['resolve'](ref)
    c.append(dict(id=sid, role='program', group=None, title=title, network=net, date=date, year=year, tier=tier,
                  commercials=ads, note=note, page=page, url=url, source=src, seconds=secs))
for sid, title, station, date, ref, kind in g['BREAKS']:
    url, secs, src, page, own = g['resolve'](ref)
    net = ('CBS / ' if station.startswith('WCCO') else 'ABC / ') + station + ' Minneapolis'
    c.append(dict(id=sid, role='station_id' if kind == 'id' else 'break', group='WCCO' if station.startswith('WCCO') else 'KSTP',
                  title=title, network=net, date=date, year=int(date[:4]) if date else None, page=page, url=url, source=src, seconds=secs))
sch = yaml.safe_load(open(tmp/'pt'/'out'/'schedules'/'1224.yml'))
save('1224', dict(number='1224', name=g['NAME'], slug=g['SLUG'], group='Holiday', collection_prefix=g['PREFIX'],
     description=yaml.safe_load(open(tmp/'pt'/'out'/f"channel-1224-{g['SLUG']}.yaml"))['channels'][0]['description'],
     schedule_description=sch['description'], sequence_key=sch['sequence'][0]['key'],
     rotation='interleave_wrap', break_groups=['WCCO', 'KSTP'], station_id_after_each_gap=True, long_reel_seconds=1200,
     style='prime_2026'), c)

# ---------- 1225 (build writes to /home/claude/xmas/out — same bytes as delivered; verified separately)
g = run(H/'xmas'/'build.py', H/'xmas')
c = []
for sid, title, net, date, year, tier, ads, ref, note in g['P']:
    url, secs, src = g['ref_url'](ref)
    page = f'https://archive.org/details/{ref[1]}' if ref[0] == 'a' else url
    c.append(dict(id=sid, role='marathon' if sid.startswith('marathon_') else 'program', group=None, title=title, network=net,
                  date=date or None, year=year, tier=tier, commercials=ads, note=note, page=page, url=url, source=src, seconds=secs))
for grp, items in (('mn', g['MN']), ('net', g['NET'])):
    for sid, title, net, date, ref in items:
        url, secs, src = g['ref_url'](ref)
        page = f'https://archive.org/details/{ref[1]}' if ref[0] == 'a' else url
        c.append(dict(id=sid, role='break', group=grp, title=title, network=net, date=date or None,
                      year=int(date[:4]) if date else None, page=page, url=url, source=src, seconds=secs))
ch = g['channel']['channels'][0]
save('1225', dict(number='1225', name=ch['name'], slug='vintage-kids-christmas', group='Holiday', collection_prefix=g['PREFIX'],
     description=ch['description'], schedule_description=g['sched']['description'], sequence_key='kids-xmas-channel',
     rotation='parity_alternate', break_groups=['mn', 'net'], station_id_after_each_gap=False, long_reel_seconds=1200,
     style='kids_2026'), c)

# ---------- holidays (build writes to /home/claude/holidays/out — same bytes as delivered)
g = run(H/'holidays'/'build_all.py', H/'holidays')
for ch in g['CHANNELS']:
    c = []
    for sid, title, net, date, year, tier, ads, ref, note in ch['programs']:
        url, secs, src, page, own = g['resolve'](ref)
        c.append(dict(id=sid, role='marathon' if sid.startswith('marathon_') else 'program', group=None, title=title, network=net,
                      date=date or None, year=year, tier=tier, commercials=ads, note=note, page=page, url=url, source=src, seconds=secs))
    for grp in ('mn', 'net'):
        for sid, title, net, date, ref in ch[grp]:
            url, secs, src, page, own = g['resolve'](ref)
            c.append(dict(id=sid, role='break', group=grp, title=title, network=net, date=date or None,
                          year=int(date[:4]) if date else None, page=page, url=url, source=src, seconds=secs))
    sch = yaml.safe_load(open(H/'holidays'/'out'/'schedules'/f"{ch['number']}.yml"))
    save(ch['number'], dict(number=ch['number'], name=ch['name'], slug=ch['slug'], group='Holiday', collection_prefix=ch['name'],
         description=ch['desc'], schedule_description=sch['description'], sequence_key=f"{ch['slug']}-channel",
         rotation='interleave_wrap', break_groups=['mn', 'net'], station_id_after_each_gap=False, long_reel_seconds=1200,
         style='kids_2026'), c)
