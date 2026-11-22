import yaml, re, importlib.util
spec=importlib.util.spec_from_file_location('b','build.py'); 
src=open('build.py').read().split("PREFIX='Vintage Kids Xmas'")[0]
ns={}; exec(src.replace("A = json.load","A = json.load").split("OUT = pathlib")[0]+"\n"+src.split("OUT = pathlib")[1].split("def dur")[0].replace("(OUT/'schedules').mkdir(parents=True, exist_ok=True)",""), ns) if False else None
exec(src.replace("(OUT/'schedules').mkdir(parents=True, exist_ok=True)",""), ns)
P,MN,NET,A,YT=ns['P'],ns['MN'],ns['NET'],ns['A'],ns['YT']
UP={'a-magical-disney-christmas-1981-cbs-version':'walt_s_vault_','a-disney-christmas-gift-12-04-1982-walt-disney-cbs':'walt_s_vault_',
'Claymation_Christmas_Celebration_CBS_WOC_1987-12-21':'vhs_deck','Muppet_Family_Christmas_ABC_WOC_1988-12-02':'vhs_deck','Mickey_Christmas_Carol_NBC_WOC_1988-12-04':'vhs_deck','charlie-brown-and-frosty-the-snowman-cbs-woc-incomplete-1986-12-12':'vhs_deck',
'Holiday_Specials_CBS_WOC_1988-11-28':'sketch_the_cow','dvd-transfer-222':'jacobburkejr','abc-the-christmas-raccoons':'takemebacktothe80s','nbc-special-mickeys-christmas-carol-1984':'takemebacktothe80s',
'80s-christmas-specials-with-commercials':'gothtv','80s-christmas-specials-with-commercials-3':'gothtv','pee-wees-playhouse-christmas-cbs-12-24-1988':'crushgals','rudolph-the-red-nose-reindeer-1989-cbs-woc':'theretroroom',
'FrostyAndFrostyReturnsCBS2004Or2005':'professorslendercat','december1991cbsbroadcastofrudolphtherednosedreindeerrecordedoffwtkrtv3':'hampton_roads_tv_fan','agarfieldchristmas12021992':'thenostalgiamall',
'tis-the-season-to-be-smurfy':'fuzzy_legends_archives','the-california-raisins-christmas-special-cbs-1987':'chadcwatson','a-garfield-christmas-1987-wfmy-cbs-2000-airing':'tyler_day736','SmokesVHSTape660':'smokenweewalt',
'TheVistaGroup-1998CBSChristmasCommercials':'the_vista_group','wsjv-28-abc-commercial-breaks-christmas-eve-1985':'indianamichigantvarchives'}
YTCH={'zVpIKt7wYuU':'TheXennial','LRcVZi-x3bw':'TheXennial','gtQJYbTemfo':'killintimeclassics','VXiHH4p51Uc':'Mickeys-Media','K-ThQtxTGZc':'mikekling','d7xCwN6-Nd4':'LouTubeR',
'saiodJr6UR8':'tcmedianow','Z71ahXqgBTM':'tcmedianow','oF7foUcyhQs':'tcmedianow','u-j7HxI89aM':'tcmedianow','KU4BeYgayXk':'tcmedianow','Nf3l8olHDB4':'tcmedianow','HzxVPmGwWC8':'tcmedianow',
'u3WC_U-rf5A':'TVsFenwick','5ftduLCmk_s':'TVsFenwick','vuq99UxjpvA':'TVsFenwick','Mbzdx70dkMU':'tvandmoviearchive','VK7zZz0N4NU':'rubysuncle','pOu70NcoSfw':'HojuKoolander','Im1So5GHeSQ':'chadyofoo','mvqwGvgcDuU':'chadyofoo',
'noFAmiMg1Kw':'misteroldschoolguy','OPwTN0zLyC4':'eastkingstonnh','DeMVGEd86Qw':'eastkingstonnh','4nak92AJATY':'RetroDakota','fQaRwV3NM1A':'tvmattkc','Ggs_txOqT04':'peppardb','fev9vp3UcsQ':'TimePodVHS'}
COLL={'a':lambda i:None}
def item_url(ref): return f'https://archive.org/details/{ref[1]}' if ref[0]=='a' else f'https://www.youtube.com/watch?v={ref[1]}'
def owner(ref):
    if ref[0]=='a':
        u=UP.get(ref[1]); return f'[@{u}](https://archive.org/details/@{u})' if u else 'uploader not shown'
    c=YTCH.get(ref[1]); return f'[@{c}](https://www.youtube.com/@{c})' if c else ''
def fmt(secs,title):
    if 'Tape' in title or 'Marathon' in title or secs>90*60 or ' + ' in title: return 'Broadcast block (several programs)'
    return 'Full-length special (~60 min)' if secs>=45*60 else 'Half-hour special'
def secs(ref):
    if ref[0]=='a': 
        f=A[ref[1]]; return next(x for x in f if x[0]==ref[2])[1] if ref[2] else f[0][1]
    return YT[ref[1]][0]
ADS={'yes':'Yes — stated in description/title','mostly':'Mostly — stated ("most have commercials")','some':'Some — stated ("some ad breaks")','label-only':'Likely — only the "WOC" (with original commercials) label in the title','unverified':'Not verified — description silent','inferred':'Inferred from runtime only'}
rows={1:[],2:[]}
for sid,title,net,date,year,tier,ads,ref,note in P:
    plat='archive.org' if ref[0]=='a' else 'YouTube'
    rows[tier].append(f"| {title} | {plat} | {net} | {date or year} | {ADS[ads]} | {fmt(secs(ref),title)} | [item]({item_url(ref)}) · {owner(ref)} | {note} |")
hdr='| Program | Platform | Network / station | Air date | Commercials & IDs | Format | Links (item · uploader) | Notes |\n|---|---|---|---|---|---|---|---|'
def brow(L):
    out=[]
    for sid,title,net,date,ref in L:
        out.append(f"| {title} | {'archive.org' if ref[0]=='a' else 'YouTube'} | {net} | {date or 'not stated'} | {round(secs(ref)/60)} min | [item]({item_url(ref)}) · {owner(ref)} |")
    return '| Break reel | Platform | Station | Date | Length | Links |\n|---|---|---|---|---|---|\n'+'\n'.join(out)
md=open('report_template.md').read()
md=md.replace('{{TIER1}}',hdr+'\n'+'\n'.join(rows[1])).replace('{{TIER2}}',hdr+'\n'+'\n'.join(rows[2])).replace('{{MN}}',brow(MN)).replace('{{NET}}',brow(NET))
md=md.replace('{{N1}}',str(len(rows[1]))).replace('{{N2}}',str(len(rows[2])))
open('out/SOURCES.md','w').write(md)
print(len(rows[1]),len(rows[2]))
