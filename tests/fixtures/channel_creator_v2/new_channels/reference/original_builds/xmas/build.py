#!/usr/bin/env python3
"""Build StreamTV channel + schedule YAML for the Vintage Kids Christmas channel."""
import json, urllib.parse, yaml, pathlib

A = json.load(open('/home/claude/xmas/archive_files.json'))
YT = json.load(open('/home/claude/xmas/yt_len.json'))
OUT = pathlib.Path('/home/claude/xmas/out'); (OUT/'schedules').mkdir(parents=True, exist_ok=True)

def dur(s):
    s=int(s); h,m,sec=s//3600,(s%3600)//60,s%60
    return 'PT'+(f'{h}H' if h else '')+(f'{m}M' if m else '')+(f'{sec}S' if sec else '') or 'PT1S'

def arch(ident, fname=None):
    files=A[ident]
    f = next(x for x in files if x[0]==fname) if fname else files[0]
    return 'https://archive.org/download/%s/%s' % (ident, urllib.parse.quote(f[0])), f[1]

# (sid, title, network/station, date or '', year, tier, ads, source, ref, note)
#  ref: ('a', identifier, filename|None) or ('y', videoId)
P = [
 # ---- 1981-1985
 ('disney_magical_xmas_1981','A Magical Disney Christmas','CBS (Walt Disney anthology)','1981-12-05',1981,1,'yes',('a','a-magical-disney-christmas-1981-cbs-version',None),'Description: includes the original commercials as aired Dec 5, 1981.'),
 ('santa_comin_wls_1981',"Santa Claus Is Comin' to Town",'ABC / WLS-TV 7 Chicago','1981-12-19',1981,1,'yes',('a','youtube-nJbsHscd3U8',None),'Complete broadcast with ABC/WLS bumpers, IDs and commercials (Museum of Classic Chicago TV mirror). YouTube original is no longer playable.'),
 ('disney_xmas_gift_1982','A Disney Christmas Gift','CBS / WISH-TV 8 Indianapolis','1982-12-04',1982,2,'unverified',('a','a-disney-christmas-gift-12-04-1982-walt-disney-cbs',None),'Betamax off-air capture; description does not say whether commercials are included.'),
 ('smurfs_xmas_nbc_1984','The Smurfs Christmas Special','NBC (affiliate not stated)','1984-12-01',1984,1,'yes',('y','zVpIKt7wYuU'),'YouTube: NBC Special Presentation with all original commercial breaks. Exact 1984 air date not stated; date set to 1984-12-01 as placeholder.'),
 ('mickey_carol_wesh_1984',"Mickey's Christmas Carol (NBC Special)",'NBC / WESH-TV Orlando','1984-12-10',1984,2,'yes',('a','nbc-special-mickeys-christmas-carol-1984',None),'Partial: first 7 minutes missing; includes original commercials.'),
 ('cabbage_patch_abc_1984',"Cabbage Patch Kids' First Christmas",'ABC (affiliate not stated)','1984-12-07',1984,1,'yes',('y','LRcVZi-x3bw'),'YouTube: original ABC broadcast with all commercial breaks (Kmart).'),
 ('christmas_raccoons_wcjb_1984','The Christmas Raccoons','ABC / WCJB-TV Gainesville','1984-12-14',1984,2,'yes',('a','abc-the-christmas-raccoons',None),'First 5 minutes missing; air date estimated by uploader.'),
 ('nbc_christmas_dream_1984','A Christmas Dream (NBC 1984 Christmas Special)','NBC','',1984,2,'label-only',('a','NBC_1984_Christmas_Special_A_Christmas_Dream_WOC','VIDEO_TS/VTS_01_1.mp4'),'Part 1 of 2. "WOC" (with original commercials) appears only in the title; kid focus not verified.'),
 ('nbc_christmas_dream_1984_p2','A Christmas Dream (NBC 1984) – Part 2','NBC','',1984,2,'label-only',('a','NBC_1984_Christmas_Special_A_Christmas_Dream_WOC','VIDEO_TS/VTS_01_2.mp4'),'Part 2 of 2.'),
 ('rudolph_wcbs_1985','Rudolph the Red-Nosed Reindeer','CBS / WCBS-TV 2 New York','1985-12-01',1985,1,'mostly',('a','dvd-transfer-222','Title 1 (Rudolph the Red-Nosed Reindeer - 1985 WCBS Recording).mp4'),'DVD Transfer 222: "most of these have the commercials included". Exact date not stated.'),
 ('cbchristmas_wcbs_1985','A Charlie Brown Christmas','CBS / WCBS-TV 2 New York','1985-12-01',1985,1,'mostly',('a','dvd-transfer-222','Title 2 (A Charlie Brown Christmas - 1985 WCBS Recording).mp4'),'DVD Transfer 222.'),
 ('twas_wcbs_1985',"'Twas the Night Before Christmas",'CBS / WCBS-TV 2 New York','1985-12-01',1985,1,'mostly',('a','dvd-transfer-222','Title 3 (Twas the Night Before Christmas - 1985 WCBS Recording).mp4'),'DVD Transfer 222.'),
 ('grinch_wcbs_1985','How the Grinch Stole Christmas!','CBS / WCBS-TV 2 New York','1985-12-07',1985,1,'mostly',('a','dvd-transfer-222','Title 5 (How the Grinch Stole Christmas - 1985 WCBS Recording).mp4'),'DVD Transfer 222: dated Dec 7, 1985 from a CBS Sportsbreak.'),
 ('frosty_wcbs_1985','Frosty the Snowman','CBS / WCBS-TV 2 New York','1985-12-07',1985,1,'mostly',('a','dvd-transfer-222','Title 6 (Frosty the Snowman - 1985 WCBS Recording).mp4'),'DVD Transfer 222: same date as the Grinch.'),
 ('heman_shera_xmas_1985','He-Man & She-Ra: A Christmas Special','Syndicated (station not stated)','1985-12-23',1985,2,'label-only',('a','he-man-and-she-ra-christmas-specail-woc-12-85',None),'Syndicated, not CBS/ABC/NBC. "WOC" in file name only.'),
 # ---- 1986-1988
 ('cb_frosty_cbs_1986','A Charlie Brown Christmas + Frosty the Snowman','CBS (affiliate not stated)','1986-12-12',1986,1,'label-only',('a','charlie-brown-and-frosty-the-snowman-cbs-woc-incomplete-1986-12-12',None),'Title says CBS, "WOC", incomplete. Same night as TCMediaNow WCCO breaks below.'),
 ('christmas_toy_katu_1986','The Christmas Toy','ABC / KATU 2 Portland','1986-12-06',1986,1,'yes',('y','gtQJYbTemfo'),'YouTube: full movie with commercials (title).'),
 ('mickey_carol_wavy_1987',"Mickey's Christmas Carol (NBC hour special)",'NBC / WAVY-TV 10 Norfolk','1987-12-04',1987,1,'yes',('a','mickeyschristmascarolnbcspecialwavytv10airingfromdecember1987',None),'Description lists the commercials that aired (Children\'s Palace, Wendy\'s, McDonald\'s, NBC promos).'),
 ('muppet_family_xmas_1987','A Muppet Family Christmas (premiere)','ABC','1987-12-16',1987,1,'yes',('a','a-muppet-family-christmas-1987-full-broadcast-w-ads-savetube.us',None),'"Full Broadcast w/ Ads" (saved from YouTube). Station not stated.'),
 ('wcco_disney_world_xmas_1987','WCCO Walt Disney World Christmas (local special)','CBS / WCCO-TV 4 Minneapolis','1987-12-15',1987,2,'unverified',('y','d7xCwN6-Nd4'),'YouTube (LouTube): local WCCO program hosted by Don Shelby and Colleen Needles; air date not stated (placeholder Dec 15, 1987); commercials not stated.'),
 ('claymation_cbs_1987','A Claymation Christmas Celebration','CBS','1987-12-21',1987,1,'yes',('a','the-california-raisins-christmas-special-cbs-1987',None),'Description: aired Dec 21, 1987 "and has the commercials".'),
 ('smurfy_wbz_1988',"'Tis the Season to Be Smurfy",'NBC (inferred) / WBZ-TV 4 Boston','1988-12-01',1988,1,'yes',('a','tis-the-season-to-be-smurfy',None),'Description: broadcast on WBZ 4 Boston with original commercials. NBC network inferred (WBZ was the NBC affiliate then).'),
 ('holiday_specials_cbs_1988','Holiday Specials (CBS, Nov 28, 1988)','CBS','1988-11-28',1988,1,'label-only',('a','Holiday_Specials_CBS_WOC_1988-11-28',None),'Contents not described; title says CBS + WOC.'),
 ('muppet_family_xmas_1988','A Muppet Family Christmas (repeat)','ABC','1988-12-02',1988,1,'label-only',('a','Muppet_Family_Christmas_ABC_WOC_1988-12-02',None),'Title says ABC + WOC.'),
 ('mickey_carol_nbc_1988',"Mickey's Christmas Carol",'NBC','1988-12-04',1988,1,'label-only',('a','Mickey_Christmas_Carol_NBC_WOC_1988-12-04',None),'Title says NBC + WOC.'),
 ('peewee_xmas_cbs_1988',"Christmas at Pee-wee's Playhouse",'CBS','1988-12-24',1988,1,'yes',('a','pee-wees-playhouse-christmas-cbs-12-24-1988',None),'Description: capture includes original commercials. (CBS premiere was Dec 21, 1988; this item is labeled Dec 24.)'),
 # ---- 1989-1994
 ('rudolph_cbs_1989','Rudolph the Red-Nosed Reindeer','CBS','1989-12-01',1989,1,'label-only',('a','rudolph-the-red-nose-reindeer-1989-cbs-woc',None),'Title: 1989 CBS WOC; 60-minute file fits a full hour slot. Exact date not stated.'),
 ('rudolph_wtkr_1991','Rudolph the Red-Nosed Reindeer','CBS / WTKR-TV 3 Norfolk','1991-12-01',1991,2,'unverified',('a','december1991cbsbroadcastofrudolphtherednosedreindeerrecordedoffwtkrtv3',None),'December 1991; description does not confirm commercials (49 minutes).'),
 ('wish_for_wings_wcbs_1991','A Wish for Wings That Work','CBS / WCBS-TV 2 New York','1991-12-18',1991,1,'yes',('y','VXiHH4p51Uc'),'YouTube: original airing with commercials; airdate Dec 18, 1991.'),
 ('xmas92_tape1','Christmas Specials Dec 1992 – Tape 1 (Charlie Brown, Garfield, Teddy Bears, Santa Claus)','CBS + ABC + Disney Channel','1992-12-01',1992,1,'some',('a','xmas921',None),'Description: "Some Ad Breaks Are Included".'),
 ('garfield_cbs_1992','A Garfield Christmas','CBS','1992-12-02',1992,1,'yes',('a','agarfieldchristmas12021992',None),'Description: commercials included; glitches at start.'),
 ('xmas92_tape2','Christmas Specials Dec 1992 – Tape 2 (Rudolph, Pooh, Frosty, Grinch)','CBS + ABC + TNT','1992-12-02',1992,2,'unverified',('a','xmas922',None),'Description lists programs only.'),
 ('town_santa_forgot_wvit_1993','The Town Santa Forgot','NBC / WVIT Hartford','1993-12-03',1993,2,'unverified',('a','thetownsantaforgot_201912','The Town Santa Forgot.mp4'),'Blank-tape item; commercials not described.'),
 ('twelve_days_wvit_1993','The Twelve Days of Christmas','NBC / WVIT Hartford','1993-12-03',1993,2,'unverified',('a','thetownsantaforgot_201912','The Twelve Days of Christmas.mp4'),''),
 ('pooh_xmas_wggb_1993','Winnie the Pooh & Christmas Too + Making of Aladdin','ABC / WGGB Springfield','1993-12-10',1993,2,'unverified',('a','thetownsantaforgot_201912','Winnie The Pooh & Christmas Too, The Making of Aladdin - A Whole New World.mp4'),'Date given only as December 1993.'),
 ('flintstone_family_wggb_1993','A Flintstone Family Christmas','ABC / WGGB Springfield','1993-12-18',1993,2,'unverified',('a','thetownsantaforgot_201912','A Flintstone Family Christmas.mp4'),''),
 ('wish_changed_wggb_1993','The Wish That Changed Christmas','ABC / WGGB Springfield','1993-12-18',1993,2,'unverified',('a','thetownsantaforgot_201912','The Wish That Changed Christmas.mp4'),''),
 ('garfield_cbs_1994','A Garfield Christmas','CBS','1994-12-14',1994,1,'yes',('a','garfield-christmas-12-14-1994',None),'Description: includes commercial breaks.'),
 # ---- 1995-2005
 ('kidswb_cbs_1995',"Mickey's Christmas Carol (CBS) + Jingle Bell Rock (ABC), 1995",'CBS + ABC (+ Kids WB 1999)','1995-12-21',1995,2,'some',('a','kidswbcbs',None),'Mixed tape: opens with Kids WB 1999 Pokémon, then the 1995 specials; "Some Ads from 1995 Are Included".'),
 ('frosty_returns_cbs_1997','Frosty Returns','CBS','1997-12-12',1997,1,'label-only',('a','Frosty_Returns_CBS_WOC_1997-12-12',None),'Title says CBS + WOC.'),
 ('story_santa_cbs_1997','The Story of Santa Claus','CBS','1997-12-12',1997,1,'label-only',('a','The_Story_Of_Santa_Claus_CBS_WOC_1997-12-12',None),'Title says CBS + WOC.'),
 ('xmas_classics_1997','Christmas TV Classics (VHS) incl. commercials – Vol 2','Not stated','1997-12-15',1997,2,'yes',('y','K-ThQtxTGZc'),'YouTube; some segments blocked by copyright per description. Network not stated.'),
 ('garfield_wfmy_2000','A Garfield Christmas (last CBS airing)','CBS / WFMY-TV 2 Greensboro','2000-12-14',2000,1,'yes',('a','a-garfield-christmas-1987-wfmy-cbs-2000-airing',None),'Description: contains original commercials from 2000.'),
 ('rudolph_cbs_2003','Rudolph the Red-Nosed Reindeer','CBS','2003-12-01',2003,2,'inferred',('a','c-2a-931a-5-aa-61-449d-a-2e-5-1aef-2e-7adf-7e-1',None),'Description just "Rudolph 2003"; commercials inferred from 61-minute runtime.'),
 ('rudolph_cbs_2004','Rudolph the Red-Nosed Reindeer','CBS','2004-12-01',2004,1,'label-only',('a','rudolph-the-red-nose-reindeer-cbs-2004-woc',None),'Title: CBS 2004 WOC (74 min, likely runs into next program).'),
 ('frosty_wtvf_2004','Frosty the Snowman + Frosty Returns','CBS / WTVF NewsChannel 5 Nashville','2004-12-01',2004,1,'yes',('a','FrostyAndFrostyReturnsCBS2004Or2005',None),'Description: 2004 or 2005 judging by commercials; notes the commercials.'),
 # ---- long marathon tapes
 ('marathon_80s_1','80s Christmas Specials With Commercials (6 hr)','Not stated','',1987,2,'yes',('a','80s-christmas-specials-with-commercials',None),'Garfield, Claymation, Sesame Street on Ice, Bugs Bunny, Santa Bear, Disney Gift, He-Man, Casper; last part is a blue screen (description).'),
 ('marathon_80s_2','80s Christmas Specials With Commercials II','Not stated','',1987,2,'yes',('a','80s-christmas-specials-with-commercials-2',None),''),
 ('marathon_80s_3','80s Christmas Specials With Commercials III','Not stated','',1987,2,'label-only',('a','80s-christmas-specials-with-commercials-3',None),''),
]

# station-break filler (commercials, bumpers, IDs) - Minnesota first
MN = [
 ('wcco_rudolph_1986_breaks','WCCO/CBS breaks during Rudolph (Dec 9, 1986)','CBS / WCCO-TV 4 Minneapolis','1986-12-09',('y','saiodJr6UR8')),
 ('wcco_cbchristmas_1986_breaks','WCCO/CBS breaks during A Charlie Brown Christmas (Dec 12, 1986)','CBS / WCCO-TV 4 Minneapolis','1986-12-12',('y','Z71ahXqgBTM')),
 ('wcco_frosty_1986_breaks','WCCO/CBS breaks during Frosty the Snowman (Dec 12, 1986)','CBS / WCCO-TV 4 Minneapolis','1986-12-12',('y','oF7foUcyhQs')),
 ('wcco_grinch_1986_breaks','WCCO/CBS breaks during the Grinch (Dec 17, 1986)','CBS / WCCO-TV 4 Minneapolis','1986-12-17',('y','u-j7HxI89aM')),
 ('wcco_twas_1986_breaks',"WCCO/CBS breaks during 'Twas the Night Before Christmas (Dec 17, 1986)",'CBS / WCCO-TV 4 Minneapolis','1986-12-17',('y','KU4BeYgayXk')),
 ('kstp_night_saved_1984_breaks','KSTP/ABC breaks during The Night They Saved Christmas (Dec 13, 1984)','ABC / KSTP-TV 5 Minneapolis','1984-12-13',('y','Nf3l8olHDB4')),
 ('kstp_xmas_commercial','KSTP Christmas commercials (undated)','ABC / KSTP-TV 5 Minneapolis','',('y','HzxVPmGwWC8')),
 ('wcco_rudolph_1992_breaks','WCCO breaks during Rudolph (Dec 11, 1992)','CBS / WCCO-TV 4 Minneapolis','1992-12-11',('y','5ftduLCmk_s')),
 ('wcco_frosty_1992_breaks','WCCO breaks during Frosty the Snowman (Dec 16, 1992)','CBS / WCCO-TV 4 Minneapolis','1992-12-16',('y','u3WC_U-rf5A')),
 ('kstp_cartoon_classics_1992','KSTP Christmas ads during Christmas Cartoon Classics (Dec 1992)','ABC / KSTP-TV 5 Minneapolis','1992-12-14',('y','vuq99UxjpvA')),
 ('wcco_christmas_day_1995','WCCO commercials, Christmas Day 1995','CBS / WCCO-TV 4 Minneapolis','1995-12-25',('y','Mbzdx70dkMU')),
 ('kstp_dec5_1991','KSTP-TV commercials (Dec 5, 1991)','ABC / KSTP-TV 5 Minneapolis','1991-12-05',('a','SmokesVHSTape660','KSTP-TV - December 5, 1991 Commercials.mp4')),
 ('kare_nov28_1991','KARE commercials, Thanksgiving Day 1991 (Macy\'s Parade)','NBC / KARE 11 Minneapolis','1991-11-28',('a','SmokesVHSTape660','KARE - November 28, 1991 Commercials.mp4')),
]
NET = [
 ('cbs_xmas_breaks_1984_85','CBS 2 New York breaks from 6 Christmas specials (1984–85)','CBS / WCBS-TV 2','1985-12-01',('y','VK7zZz0N4NU')),
 ('cbs_frosty_1986_breaks','CBS breaks during Frosty the Snowman (1986)','CBS','1986-12-01',('y','pOu70NcoSfw')),
 ('cbs_frosty_cb_kcci','CBS breaks: Frosty & Charlie Brown (TV8 Des Moines)','CBS / KCCI 8 Des Moines','',('y','Im1So5GHeSQ')),
 ('nbc_smurfs_chipmunks_1987','NBC breaks: Smurfs & Chipmunks specials (Dec 1987)','NBC / WMTV 15 Madison','1987-12-01',('y','mvqwGvgcDuU')),
 ('peewee_wbns_1988_break',"CBS break during Pee-wee's Playhouse Christmas (Dec 21, 1988)",'CBS / WBNS-TV 10 Columbus','1988-12-21',('y','noFAmiMg1Kw')),
 ('nbc_wndu_1988','WNDU/NBC breaks (Dec 12, 1988)','NBC / WNDU-TV 16 South Bend','1988-12-12',('a','wndu-16-nbc-commercial-breaks-12-12-1988-both-partial-and-complete-breaks',None)),
 ('cbs_rudolph_1990_breaks','CBS Rudolph complete breaks (1990)','CBS / KHQA-TV','1990-12-01',('y','OPwTN0zLyC4')),
 ('abc_pooh_1991_breaks','ABC breaks during Winnie the Pooh and Christmas Too (Dec 14, 1991)','ABC / KSFY','1991-12-14',('y','4nak92AJATY')),
 ('cbs_rudolph_1993_breaks','CBS Rudolph breaks (KCTV5, Dec 1993)','CBS / KCTV 5 Kansas City','1993-12-01',('y','fQaRwV3NM1A')),
 ('cbs_cb_garfield_1993_breaks','CBS breaks: Charlie Brown / Garfield (1993)','CBS','1993-12-01',('y','Ggs_txOqT04')),
 ('cbs_rudolph_1994_breaks','CBS Rudolph breaks (1994)','CBS','1994-12-01',('y','fev9vp3UcsQ')),
 ('cbs_xmas_1998_lasvegas','CBS affiliate holiday breaks, Las Vegas (Dec 1998)','CBS (Las Vegas affiliate)','1998-12-01',('a','TheVistaGroup-1998CBSChristmasCommercials',None)),
 ('cbs_garfield_1999_breaks','CBS breaks during A Garfield Christmas (Dec 11, 1999)','CBS','1999-12-11',('a','a-garfield-christmas-commercial-breaks-dec.-1999-cbs',None)),
 ('cbs_rudolph_1999_breaks','CBS Rudolph complete breaks (1999)','CBS','1999-12-01',('y','DeMVGEd86Qw')),
]

PREFIX='Vintage Kids Xmas'
streams=[]; prog_keys=[]
def ref_url(ref):
    if ref[0]=='a':
        return arch(ref[1], ref[2])+( 'archive',)
    return ('https://www.youtube.com/watch?v='+ref[1], YT[ref[1]][0], 'youtube')

for sid,title,net,date,year,tier,ads,ref,note in P:
    url,secs,src=ref_url(ref)
    coll=f'{PREFIX} - {title} ({net.split(" /")[0].split(" (")[0]} {year}) [{sid}]'
    s={'id':sid,'collection':coll,'type':'event','year':year,'slot':f'{title} ({net}{", "+date if date else ""})',
       'network':net,'runtime':dur(secs),'source':src,'url':url,
       'notes':f'Tier {tier}; commercials: {ads}. {note} Page: '+( f'https://archive.org/details/{ref[1]}' if ref[0]=='a' else url)}
    if date: s['broadcast_date']=date
    streams.append(s); prog_keys.append((sid,coll,s['slot']))
break_keys={'mn':[], 'net':[]}; long_breaks=[]
for group,items in (('mn',MN),('net',NET)):
    for sid,title,net,date,ref in items:
        url,secs,src=ref_url(ref)
        coll=f'{PREFIX} - Break - {title} [{sid}]'
        s={'id':sid,'collection':coll,'type':'commercial','slot':title,'network':net,'runtime':dur(secs),'source':src,'url':url,
           'notes':'Commercial/bumper break reel. Page: '+(f'https://archive.org/details/{ref[1]}' if ref[0]=='a' else url)}
        if date: s['broadcast_date']=date; s['year']=int(date[:4])
        streams.append(s)
        (long_breaks if secs>20*60 else break_keys[group]).append((sid,coll,title))
channel={'channels':[{'number':'1225','name':'Vintage Kids Christmas','group':'Holiday',
  'description':'Children\'s Christmas specials as broadcast on CBS, ABC and NBC (plus WCCO/KSTP/KARE breaks), 1981-2005, from off-air VHS/Beta captures with original commercials, bumpers and station IDs.',
  'enabled':True,'streams':streams}]}
yaml.safe_dump(channel, open(OUT/'channel-1225-vintage-kids-christmas.yaml','w'), sort_keys=False, allow_unicode=True, width=200)

content=[{'key':k,'collection':c,'order':'chronological'} for k,c,_ in prog_keys]
allbreaks=break_keys['mn']+break_keys['net']+long_breaks
content+=[{'key':k,'collection':c,'order':'chronological'} for k,c,_ in allbreaks]
# round-robin: after each program play ONE short break reel, alternating Minnesota and network reels
mn=break_keys['mn']; nt=break_keys['net']; items=[]; im=inn=0
marathon=[x for x in prog_keys if x[0].startswith('marathon_')]
order={sid:(date or f'{year}-12-31') for sid,_,_,date,year,*_ in P}
regular=sorted([x for x in prog_keys if not x[0].startswith('marathon_')], key=lambda x: order[x[0]])
for i,(k,c,slot) in enumerate(regular):
    items.append({'all':k,'custom_title':slot})
    if i%2==0: b=mn[im%len(mn)]; im+=1
    else: b=nt[inn%len(nt)]; inn+=1
    items.append({'all':b[0],'custom_title':'Station Break: '+b[2],'filler_kind':'Commercial'})
for k,c,slot in long_breaks:
    items.append({'all':k,'custom_title':'Commercial Break Marathon: '+slot,'filler_kind':'Commercial'})
for k,c,slot in marathon:
    items.append({'all':k,'custom_title':slot})
seq=[{'key':'kids-xmas-channel','items':items}]
sched={'name':'1225 Vintage Kids Christmas','description':'Chronological run (1981 -> 2005) of off-air kids Christmas broadcasts; one vintage station-break reel (alternating Minnesota WCCO/KSTP/KARE and CBS/ABC/NBC network reels) between programs, then long commercial reels and multi-hour marathon tapes. Loops.',
       'media':{'preferred_extension':'mp4','mp4_only':True},'content':content,'sequence':seq,'playout':[{'sequence':'kids-xmas-channel'},{'repeat':True}]}
yaml.safe_dump(sched, open(OUT/'schedules'/'1225.yml','w'), sort_keys=False, allow_unicode=True, width=200)

# flat URL list (tab-separated) for anything else
with open(OUT/'urls.tsv','w') as f:
    f.write('id\ttype\tnetwork\tdate\truntime\turl\n')
    for s in streams: f.write(f"{s['id']}\t{s['type']}\t{s['network']}\t{s.get('broadcast_date','')}\t{s['runtime']}\t{s['url']}\n")
print(len(P),'programs,',len(MN)+len(NET),'break reels')
