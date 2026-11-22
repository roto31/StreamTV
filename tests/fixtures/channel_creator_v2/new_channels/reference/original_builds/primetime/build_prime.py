#!/usr/bin/env python3
"""Build channel 1224 Vintage Prime Time Christmas (channel YAML, schedule, urls.tsv, SOURCES.md)."""
import urllib.parse, yaml, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from prime_data import PROGRAMS, BREAKS

NUM, NAME, SLUG, PREFIX = '1224', 'Vintage Prime Time Christmas', 'vintage-prime-time-christmas', 'Prime Time Xmas'
OUT = pathlib.Path(__file__).parent / 'out'
(OUT / 'schedules').mkdir(parents=True, exist_ok=True)

def dur(s):
    s = int(s); h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return ('PT' + (f'{h}H' if h else '') + (f'{m}M' if m else '') + (f'{sec}S' if sec else '')) if s else 'PT1S'

def resolve(ref):
    if ref[0] == 'a':
        _, ident, fname, secs, u = ref
        url = 'https://archive.org/download/%s/%s' % (ident, urllib.parse.quote(fname))
        own = f'[@{u}](https://archive.org/details/@{u})' if u else 'uploader not shown'
        return url, secs, 'archive', f'https://archive.org/details/{ident}', own
    _, vid, secs, h = ref
    url = 'https://www.youtube.com/watch?v=' + vid
    return url, secs, 'youtube', url, f'[{h}](https://www.youtube.com/{h})'

streams, progs, reels, ids, longs = [], [], {'WCCO': [], 'KSTP': []}, [], []
for sid, title, net, date, year, tier, ads, ref, note in PROGRAMS:
    url, secs, src, page, own = resolve(ref)
    short = net.split(' /')[0].split(' (')[0]
    coll = f'{PREFIX} - {title} ({short} {year}) [{sid}]'
    slot = f'{title} ({net}, {date})' if date else f'{title} ({net}, {year})'
    s = {'id': sid, 'collection': coll, 'type': 'event', 'year': year, 'broadcast_date': date, 'slot': slot,
         'network': net, 'runtime': dur(secs), 'source': src, 'url': url,
         'notes': f'Tier {tier}; commercials: {ads}. {note} Page: {page}'}
    streams.append(s)
    progs.append(dict(sid=sid, coll=coll, slot=slot, title=title, net=net, date=date, year=year, tier=tier,
                      ads=ads, secs=secs, src=src, page=page, own=own, note=note))
for sid, title, station, date, ref, kind in BREAKS:
    url, secs, src, page, own = resolve(ref)
    net = ('CBS / ' if station.startswith('WCCO') else 'ABC / ') + station + ' Minneapolis'
    coll = f'{PREFIX} - Break - {title} [{sid}]'
    s = {'id': sid, 'collection': coll, 'type': 'commercial', 'slot': title, 'network': net, 'runtime': dur(secs),
         'source': src, 'url': url,
         'notes': ('Station holiday promo / ID. ' if kind == 'id' else 'Commercial break reel. ') + 'Page: ' + page}
    if date: s['broadcast_date'] = date; s['year'] = int(date[:4])
    streams.append(s)
    rec = dict(sid=sid, coll=coll, title=title, station=station, date=date, secs=secs, src=src, page=page, own=own, kind=kind)
    if kind == 'id': ids.append(rec)
    elif secs > 20 * 60: longs.append(rec)
    else: reels['WCCO' if station.startswith('WCCO') else 'KSTP'].append(rec)

desc = ("Prime-time Christmas movies and specials as broadcast on CBS and ABC, 1980-1999, many complete with their original "
        "holiday commercials; WCCO 4 and KSTP 5 holiday commercial reels and station IDs play between programs.")
yaml.safe_dump({'channels': [{'number': NUM, 'name': NAME, 'group': 'Holiday', 'description': desc, 'enabled': True,
                              'streams': streams}]},
               open(OUT / f'channel-{NUM}-{SLUG}.yaml', 'w'), sort_keys=False, allow_unicode=True, width=200)

# ---- schedule: programs oldest -> newest; each gap = one WCCO or KSTP reel (alternating) + one station promo
order = sorted(progs, key=lambda p: p['date'] or f"{p['year']}-12-31")
w, k = reels['WCCO'], reels['KSTP']
rot = []
for i in range(max(len(w), len(k))):
    if i < len(w): rot.append(w[i])
    if i < len(k): rot.append(k[i])
items = []
n = max(len(order), len(rot))   # every reel is used at least once per loop
gaps = [[] for _ in order]
for i in range(n): gaps[i % len(order)].append(rot[i % len(rot)])
for i, (p, g) in enumerate(zip(order, gaps)):
    items.append({'all': p['sid'], 'custom_title': p['slot']})
    for b in g:
        items.append({'all': b['sid'], 'custom_title': 'Station Break: ' + b['title'], 'filler_kind': 'Commercial'})
    pr = ids[i % len(ids)]
    items.append({'all': pr['sid'], 'custom_title': 'Station ID: ' + pr['title'], 'filler_kind': 'Commercial'})
for b in longs:
    items.append({'all': b['sid'], 'custom_title': 'Commercial Break Marathon: ' + b['title'], 'filler_kind': 'Commercial'})
content = [{'key': p['sid'], 'collection': p['coll'], 'order': 'chronological'} for p in progs]
content += [{'key': b['sid'], 'collection': b['coll'], 'order': 'chronological'} for b in w + k + longs + ids]
key = f'{SLUG}-channel'
sched = {'name': f'{NUM} {NAME}',
         'description': 'Chronological run (1980 -> 1999) of CBS/ABC prime-time Christmas movies and specials; after each program one WCCO or KSTP holiday commercial reel (alternating) and a WCCO/KSTP Christmas station ID, then three long KSTP reels. Loops.',
         'media': {'preferred_extension': 'mp4', 'mp4_only': True}, 'content': content,
         'sequence': [{'key': key, 'items': items}], 'playout': [{'sequence': key}, {'repeat': True}]}
yaml.safe_dump(sched, open(OUT / 'schedules' / f'{NUM}.yml', 'w'), sort_keys=False, allow_unicode=True, width=200)

with open(OUT / 'urls.tsv', 'w') as f:
    f.write('id\ttype\tnetwork\tdate\truntime\turl\n')
    for s in streams: f.write(f"{s['id']}\t{s['type']}\t{s['network']}\t{s.get('broadcast_date','')}\t{s['runtime']}\t{s['url']}\n")

# ---- SOURCES.md
ADS = {'yes': 'Yes — stated by the uploader', 'label-only': 'Likely — only the "WOC" label in the title',
       'unverified': 'Not verified — description silent', 'inferred': 'Inferred from runtime only', 'no': 'No — removed'}
def fmt(secs, title):
    if secs >= 100 * 60: return 'Movie (2-hour slot)'
    if secs >= 45 * 60: return 'Special (1-hour slot)'
    return 'Special (half-hour slot)'
hdr = '| Program | Platform | Network / station | Air date | Commercials | Format | Links (item · uploader) | Notes |\n|---|---|---|---|---|---|---|---|'
def prow(p):
    return (f"| {p['title']} | {'archive.org' if p['src']=='archive' else 'YouTube'} | {p['net']} | {p['date'] or p['year']} | "
            f"{ADS[p['ads']]} | {fmt(p['secs'], p['title'])} | [item]({p['page']}) · {p['own']} | {p['note']} |")
def brows(L):
    rows = [f"| {b['title']} | {'archive.org' if b['src']=='archive' else 'YouTube'} | {b['date'] or 'not stated'} | "
            f"{max(1, round(b['secs']/60))} min | [item]({b['page']}) · {b['own']} |" for b in L]
    return '| Reel | Platform | Date | Length | Links |\n|---|---|---|---|---|\n' + '\n'.join(rows)
t1 = [p for p in order if p['tier'] == 1]; t2 = [p for p in order if p['tier'] == 2]
allw = [b for b in w + longs + ids if b['station'].startswith('WCCO')]
allk = [b for b in k + longs + ids if b['station'].startswith('KSTP')]
md = f"""# {NAME} — StreamTV channel {NUM}: sources

Researched November 22, 2026 on archive.org and YouTube. Every row links to the page its facts came from.

Channel {NUM} plays CBS and ABC prime-time Christmas movies and specials from 1980 to 1999 in air-date order. After each program it plays one real WCCO 4 or KSTP 5 holiday commercial reel (alternating stations) and a short WCCO or KSTP Christmas station ID. Nothing from channel 1225 (the kids' animated specials) is repeated here except some of the same WCCO/KSTP break reels.

## Plain-language terms

- **Off-air recording** — a home VHS or Betamax tape of the TV signal as it aired, later digitized. It keeps the commercials, bumpers and station IDs.
- **Complete airing** — the whole broadcast slot, program plus the commercials that ran during it.
- **Commercials removed** — the uploader edited the ads out. The program is complete, but you don't see the original breaks.
- **Station ID / promo** — the short "Happy Holidays from WCCO 4" type spots stations ran between programs.
- **O&O / affiliate** — WCCO was CBS's Twin Cities station; KSTP was the ABC affiliate. Local stations ran their own local ads inside network breaks.
- **WOC** — "with original commercials", a label some uploaders put in titles.
- **Tier 1 / Tier 2** — Tier 1: a CBS or ABC prime-time Christmas program from the 1980s–90s, complete, with the original commercials confirmed by the uploader or title. Tier 2: one of those is missing (commercials removed or not confirmed, network not stated, or a WCCO-produced local special).

## Tier 1 — complete airings with commercials ({len(t1)})

{hdr}
""" + '\n'.join(prow(p) for p in t1) + f"""

## Tier 2 — partial matches ({len(t2)})

{hdr}
""" + '\n'.join(prow(p) for p in t2) + f"""

## WCCO 4 and KSTP 5 holiday reels and station IDs (between programs)

Reels over 20 minutes play as a block at the end of each loop.

### WCCO-TV 4 (CBS)

{brows(allw)}

### KSTP-TV 5 (ABC)

{brows(allk)}

## Collections and channels worth following

| Collection / channel | Platform | Why it matters | Link |
|---|---|---|---|
| TCMediaNow (Twin Cities Media Now) | YouTube | The only source found for complete Minnesota airings: A Christmas Carol off WCCO (1986), The Best Christmas Pageant Ever off KSTP (1984), plus the 1986 WCCO and 1984 KSTP holiday breaks, WCCO local specials and station promos. | https://www.youtube.com/@tcmedianow |
| tvandmoviearchive | YouTube + archive.org | WCCO and KSTP commercial reels by exact date, with every ad listed (WCCO Christmas Day 1995, KSTP Dec 1994/1997/1999). | https://www.youtube.com/@tvandmoviearchive |
| Smoke's VHS/DVR Collection | YouTube + archive.org | Twin Cities off-air tapes split into dated reels (WCCO Dec 1997, KSTP Dec 3, 1989 and Dec 5, 1991). | https://archive.org/details/smokesvhsdvrcollection |
| FenwickTV | YouTube | Tape #535: WCCO and KSTP Christmas ads from December 1992. | https://www.youtube.com/@TVsFenwick |
| @joe_gariffo | archive.org | Prime-time CBS/ABC Christmas broadcasts with commercials: Dolly Parton 1990, Disney's Christmas Fantasy on Ice 1992, Christmas on Division Street 1993, A Christmas Carol 1986. | https://archive.org/details/@joe_gariffo |
| Randolph Stevens | YouTube | Complete 1980s–90s CBS/ABC Christmas variety specials (Perry Como, Andy Williams, John Denver, Opryland), usually with commercials removed. Good for adding more specials. | https://www.youtube.com/@randolphstevens6664 |
| Kev The Ripper | YouTube | "Full Special with Original Commercials" uploads (Christmas at Home with the Stars, ABC 1994). | https://www.youtube.com/@kevripzzz |
| The Museum of Classic Chicago Television | YouTube (mirrored on archive.org) | Complete WBBM/WLS broadcasts with every break itemized (A Christmas Without Snow, CBS 1980). | https://www.youtube.com/@FuzzyMemoriesTV |

## Also found, not loaded into the channel

- **Duplicates kept as backups**: [A Christmas Carol, CBS 1986 with commercials](https://archive.org/details/a-christmas-carol-1984-cbs-broadcast-1986) (use it if the WCCO copy goes away); [Ernest Saves Christmas, WGGB/ABC 12/11/1993](https://archive.org/details/wggb-abc-40-ernest-saves-xmas-12-11-1993) ("a bit of commercials"); [Mrs. Santa Claus + Walker, Texas Ranger, CBS 1997](https://archive.org/details/cbs-mrs-santa-clause-1997-walker-epi-run) (2½ h tape); [Perry Como 1981 YouTube copy](https://www.youtube.com/watch?v=46kF9bpIh4o); [Kenny & Dolly YouTube copy](https://www.youtube.com/watch?v=4Rla8OkFKTE); [John Denver Christmas in Aspen, archive.org](https://archive.org/details/john-denvers-christmas-in-aspen) (40 min).
- **Long mixed tapes**: [ABC Saturday Night Movie Ernest Saves Christmas (WLKY 12/14/1991) + CBS Turner & Hooch + news, all with commercials](https://archive.org/details/abc-cbs-wlky-abc-saturday-night-movie-ernest-saves-christmas-december-14-1991-cb) (4½ h); [ABC New Kids on the Block Christmas special + Going Places + 20/20, 12/14/1990](https://archive.org/details/abc-new-kids-on-the-block-christmas-special-going-places-20-20-december-14-1990_202603) (2 h, mostly not Christmas).
- **Before 1980**: [ABC Theatre "The Gathering", WTVN complete broadcast 12/10/1978](https://www.youtube.com/watch?v=8hvXCtv8_2Q); [WCCO commercials during "White Christmas", 12/21/1979](https://www.youtube.com/watch?v=6F-yA1bVpvw).
- **Not CBS/ABC or not a real airing**: Christmas Eve with Loretta Young (KARE/NBC 1986, with commercials); An American Country Christmas + Kenny Rogers: The Gift (Family Channel 1996); A Smoky Mountain Christmas (a 2022 recording); "A Very Brady Christmas" uploads labeled "The Baseball Network" (a fan-made fake network, not the 1988 CBS airing).
- **Only breaks or promos survive**: A Very Brady Christmas (CBS 1988, breaks only, KCCI Des Moines), The Christmas Box (CBS 1995, KMOV breaks only), Scrooged and Santa Claus: The Movie (ABC, breaks only from other cities), Julie Andrews' Sound of Christmas (WABC break).

## Search gaps and items that could not be verified

- **Complete Minnesota airings are rare.** Only two were found: A Christmas Carol (WCCO 1986) and The Best Christmas Pageant Ever (KSTP 1984). Everything else is from other cities, with WCCO/KSTP reels between programs.
- **Popular CBS/ABC Christmas movies with no surviving full airing found**: A Very Brady Christmas (1988), Christmas Comes to Willow Creek (1987), The Christmas Gift (1986), The Christmas Box (1995), The Gift of Love (1983), and network airings of theatrical movies (Home Alone, The Santa Clause, Scrooged).
- **Placeholder dates**: items marked "placeholder" in their notes have a month and year but no day.
- **"Commercials removed"**: Tier 2 variety specials from Randolph Stevens are complete but edited. They keep the channel's prime-time feel; the WCCO/KSTP reels supply the ads.
- **1980s vs 1990s balance**: WCCO/KSTP reels cover 1984–1999; no WCCO/KSTP December reel from 1980–1983 was found.
- **YouTube reliability**: videos can disappear or be blocked. Run the installer's URL check before each season.
"""
open(OUT / 'SOURCES.md', 'w').write(md)
tot = sum(p['secs'] for p in progs) + sum(b['secs'] for b in w + k + longs + ids)
print(f'{len(progs)} programs ({len(t1)} tier 1), {len(w)+len(k)} short reels, {len(longs)} long reels, {len(ids)} IDs; {tot/3600:.1f} h of media; {len(items)} schedule items')
