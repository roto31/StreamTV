### turn05.txt call 12: mcp__remote-devices__Claude_Browser__navigate
```
https://www.youtube.com/results?search_query=WCCO+christmas+commercials
```

### turn05.txt call 13: mcp__remote-devices__Claude_Browser__javascript_tool
```
async function yt(q){
  const h = await fetch('https://www.youtube.com/results?search_query='+encodeURIComponent(q)+'&sp=EgIQAQ%253D%253D').then(r=>r.text());
  const m = h.match(/var ytInitialData = (\{.*?\});<\/script>/s);
  if(!m) return ['noparse'];
  const d = JSON.parse(m[1]);
  const out=[];
  const walk=o=>{ if(!o||typeof o!=='object') return; if(o.videoRenderer){const v=o.videoRenderer; out.push(`${v.videoId} | ${v.title?.runs?.[0]?.text} | ${v.ownerText?.runs?.[0]?.text} ${v.ownerText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.canonicalBaseUrl||''} | ${v.lengthText?.simpleText||''} | ${v.publishedTimeText?.simpleText||''}`);return;} for(const k in o) walk(o[k]); };
  walk(d); return out.slice(0,20);
}
const qs=['WCCO christmas commercials','KSTP christmas commercials','KCCO christmas','WCCO Charlie Brown Christmas 1986','KSTP Rudolph','TCMediaNow christmas','CBS Christmas special with commercials 1980s','ABC Christmas special original broadcast commercials 1980s','NBC Christmas special with commercials 1987','Muppet Family Christmas original broadcast commercials','Garfield Christmas CBS commercials','Rudolph CBS 1990s with commercials','Frosty the Snowman CBS commercials 1980s','Winnie the Pooh and Christmas Too ABC 1991 commercials','Claymation Christmas Celebration CBS commercials','He-Man She-Ra Christmas special 1985 commercials','Christmas specials VHS commercials 1990s full tape','Year Without a Santa Claus ABC commercials','A Charlie Brown Christmas CBS 1980s commercials','Pee-wee Playhouse Christmas CBS 1988 commercials'];
const res={};
for(const q of qs){ res[q]=await yt(q); }
Object.entries(res).map(([k,v])=>'### '+k+'\n'+v.join('\n')).join('\n')
```

### turn05.txt call 17: mcp__remote-devices__Claude_Browser__javascript_tool
```
async function yt(q,sp){
  const h = await fetch('https://www.youtube.com/results?search_query='+encodeURIComponent(q)+'&sp='+(sp||'EgIQAQ%253D%253D')).then(r=>r.text());
  const m = h.match(/var ytInitialData = (\{.*?\});<\/script>/s);
  if(!m) return ['noparse'];
  const d = JSON.parse(m[1]); const out=[];
  const walk=o=>{ if(!o||typeof o!=='object') return;
   if(o.videoRenderer){const v=o.videoRenderer; const L=v.lengthText?.simpleText||''; if(L.split(':').length>=3 || parseInt(L)>=20) out.push(`${v.videoId} | ${v.title?.runs?.[0]?.text} | ${v.ownerText?.runs?.[0]?.text} ${v.ownerText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.canonicalBaseUrl||''} | ${L}`);return;}
   if(o.lockupViewModel && o.lockupViewModel.contentType==='LOCKUP_CONTENT_TYPE_PLAYLIST'){const l=o.lockupViewModel; out.push(`PL ${l.contentId} | ${l.metadata?.lockupMetadataViewModel?.title?.content} | ${JSON.stringify(l.metadata?.lockupMetadataViewModel?.metadata?.contentMetadataViewModel?.metadataRows?.[0]?.metadataParts?.map(p=>p.text?.content)||'')}`);return;}
   if(o.playlistRenderer){const p=o.playlistRenderer; out.push(`PL ${p.playlistId} | ${p.title?.simpleText} | ${p.shortBylineText?.runs?.[0]?.text} | ${p.videoCount}`);return;}
   for(const k in o) walk(o[k]); };
  walk(d); return out.slice(0,15);
}
const qs=['Christmas special full broadcast original commercials 1980s','Christmas special full broadcast commercials 1990s CBS','Rudolph the Red-Nosed Reindeer CBS full broadcast commercials','Frosty the Snowman CBS full broadcast with commercials','A Charlie Brown Christmas CBS full broadcast commercials','A Garfield Christmas full broadcast commercials','Claymation Christmas Celebration full broadcast commercials','Winnie the Pooh and Christmas Too ABC full broadcast','Santa Claus is Comin to Town ABC full broadcast commercials','Mickey\'s Christmas Carol NBC full broadcast commercials','Christmas Toy 1986 ABC full broadcast commercials','A Wish for Wings That Work CBS 1991 commercials','Its Christmastime Again Charlie Brown 1992 CBS commercials','Disney Christmas special CBS full broadcast commercials','How the Grinch Stole Christmas CBS 1980s full broadcast commercials'];
const res={}; for(const q of qs){res[q]=await yt(q);}
const pls={}; for(const q of ['christmas specials with commercials','80s christmas specials original broadcast','vintage christmas specials VHS commercials']){pls[q]=await yt(q,'EgIQAw%253D%253D');}
Object.entries(res).map(([k,v])=>'### '+k+'\n'+v.join('\n')).join('\n')+'\n=====PLAYLISTS\n'+Object.entries(pls).map(([k,v])=>'### '+k+'\n'+v.join('\n')).join('\n')
```

### turn05.txt call 18: mcp__remote-devices__Claude_Browser__javascript_tool
```
const ids='saiodJr6UR8 Z71ahXqgBTM oF7foUcyhQs u-j7HxI89aM KU4BeYgayXk Nf3l8olHDB4 HzxVPmGwWC8 u3WC_U-rf5A 5ftduLCmk_s vuq99UxjpvA Mbzdx70dkMU d7xCwN6-Nd4 YOtHvFYgq6c 2qKtdmfTT9Y fFqan3_zvuA zWYndh3GmVM LRcVZi-x3bw gtQJYbTemfo 7dr15Utx-NM VXiHH4p51Uc GpdO9Oylw74 iKZNA-QnyEo K-ThQtxTGZc KXPMH_u6Z8w 6XNphu7llWc mvqwGvgcDuU Im1So5GHeSQ VK7zZz0N4NU QrHyY70EtWw nJbsHscd3U8 lh83ojuAkx8 jRnizx1E4u8 4nak92AJATY cjgYj19OYqI'.split(' ');
const res=[];
for(const id of ids){
 try{
 const h=await fetch('https://www.youtube.com/watch?v='+id).then(r=>r.text());
 const m=h.match(/var ytInitialPlayerResponse = (\{.*?\});(?:var|<\/script>)/s);
 if(!m){res.push(id+' noparse');continue;}
 const p=JSON.parse(m[1]); const v=p.videoDetails||{}; const mf=p.microformat?.playerMicroformatRenderer||{};
 res.push(`## ${id} | ${v.title} | ${v.author} | ${Math.round((+v.lengthSeconds||0)/60)}min | pub ${mf.publishDate||''} | status ${p.playabilityStatus?.status}\n${(v.shortDescription||'').replace(/\s+/g,' ').slice(0,450)}`);
 }catch(e){res.push(id+' ERR '+e)}
}
res.join('\n')
```

### turn05.txt call 19: mcp__remote-devices__Claude_Browser__javascript_tool
```
async function page(u){const h=await fetch(u).then(r=>r.text());const m=h.match(/var ytInitialData = (\{.*?\});<\/script>/s);return m?JSON.parse(m[1]):null;}
const out=[];
for (const ch of ['@tcmedianow','@TVsFenwick','@FuzzyMemoriesTV','@kevripzzz','@TheXennial']){
 const d=await page('https://www.youtube.com/'+ch+'/playlists');
 const pl=[]; const walk=o=>{if(!o||typeof o!=='object')return; if(o.lockupViewModel&&o.lockupViewModel.contentType==='LOCKUP_CONTENT_TYPE_PLAYLIST'){pl.push(o.lockupViewModel.contentId+' | '+o.lockupViewModel.metadata?.lockupMetadataViewModel?.title?.content);return;} if(o.gridPlaylistRenderer){pl.push(o.gridPlaylistRenderer.playlistId+' | '+(o.gridPlaylistRenderer.title?.runs?.[0]?.text||o.gridPlaylistRenderer.title?.simpleText));return;} for(const k in o)walk(o[k]);}; walk(d);
 out.push('### '+ch+'\n'+pl.filter(x=>/christ|holi|xmas|dec|santa|winter|special/i.test(x)).join('\n')+'\n(all: '+pl.length+')');
}
async function yt(q){const d=await page('https://www.youtube.com/results?search_query='+encodeURIComponent(q)+'&sp=EgIQAQ%253D%253D');const o2=[];const walk=o=>{if(!o||typeof o!=='object')return;if(o.videoRenderer){const v=o.videoRenderer;o2.push(`${v.videoId} | ${v.title?.runs?.[0]?.text} | ${v.ownerText?.runs?.[0]?.text} | ${v.lengthText?.simpleText||''}`);return;}for(const k in o)walk(o[k]);};walk(d);return o2.slice(0,12);}
for(const q of ['FenwickTV Tape 535','Kev The Ripper Christmas full special original commercials','Lost Classics from a Xennial Childhood Christmas original broadcast','KARE 11 Christmas special commercials 1980s']) out.push('### '+q+'\n'+(await yt(q)).join('\n'));
out.join('\n')
```

### turn05.txt call 20: mcp__remote-devices__Claude_Browser__javascript_tool
```
const res=[];
for(const id of 'TtzUkLXE5-g zVpIKt7wYuU OPwTN0zLyC4 DeMVGEd86Qw fev9vp3UcsQ fQaRwV3NM1A pOu70NcoSfw Ggs_txOqT04 noFAmiMg1Kw MBONQCKotBY rXuvauZEt84 HzxVPmGwWC8'.split(' ')){
 const h=await fetch('https://www.youtube.com/watch?v='+id).then(r=>r.text());
 const m=h.match(/var ytInitialPlayerResponse = (\{.*?\});(?:var|<\/script>)/s);
 const p=JSON.parse(m[1]); const v=p.videoDetails||{};
 res.push(`## ${id} | ${v.title} | ${v.author} | ${Math.round((+v.lengthSeconds||0)/60)}min | ${p.playabilityStatus?.status}\n${(v.shortDescription||'').replace(/\s+/g,' ').slice(0,300)}`);
}
for(const pl of ['PLCremF6kRyQjynqlr73lLAS32HDrETOGU','PLSvjlEPnm7jG8gvHB2sLWPwWJpN3c3N8-','PLpTpgw8or0jllJgMNwYGBn_xpUKGDZy3o']){
 const h=await fetch('https://www.youtube.com/playlist?list='+pl).then(r=>r.text());
 const m=h.match(/var ytInitialData = (\{.*?\});<\/script>/s); const d=JSON.parse(m[1]); const vids=[];
 const walk=o=>{if(!o||typeof o!=='object')return; if(o.playlistVideoRenderer){const v=o.playlistVideoRenderer; vids.push(`${v.videoId} | ${v.title?.runs?.[0]?.text} | ${v.shortBylineText?.runs?.[0]?.text} | ${v.lengthText?.simpleText||''}`);return;} for(const k in o)walk(o[k]);}; walk(d);
 const owner = (h.match(/"ownerText":\{"runs":\[\{"text":"([^"]+)"/)||[])[1];
 res.push(`### PLAYLIST ${pl} owner:${owner} n=${vids.length}\n`+vids.slice(0,40).join('\n'));
}
res.join('\n')
```

### turn05.txt call 22: mcp__remote-devices__Claude_Browser__navigate
```
https://archive.org/
```

### turn05.txt call 23: mcp__remote-devices__Claude_Browser__javascript_tool
```
const ids=`a-magical-disney-christmas-1981-cbs-version
a-disney-christmas-gift-12-04-1982-walt-disney-cbs
the-california-raisins-christmas-special-cbs-1987
Claymation_Christmas_Celebration_CBS_WOC_1987-12-21
claymationchristmas480p
garfield-christmas-12-14-1994
agarfieldchristmas12021992
a-garfield-christmas-1987-wfmy-cbs-2000-airing
a-garfield-christmas-commercial-breaks-dec.-1999-cbs
charlie-brown-and-frosty-the-snowman-cbs-woc-incomplete-1986-12-12
december1991cbsbroadcastofrudolphtherednosedreindeerrecordedoffwtkrtv3
rudolph-the-red-nose-reindeer-1989-cbs-woc
rudolph-the-red-nose-reindeer-cbs-2004-woc
c-2a-931a-5-aa-61-449d-a-2e-5-1aef-2e-7adf-7e-1
FrostyAndFrostyReturnsCBS2004Or2005
Frosty_Returns_CBS_WOC_1997-12-12
The_Story_Of_Santa_Claus_CBS_WOC_1997-12-12
pee-wees-playhouse-christmas-cbs-12-24-1988
Holiday_Specials_CBS_WOC_1988-11-28
xmas921
xmas922
kidswbcbs
dvd-transfer-222
dvd-transfer-161
dvd-transfer-190
dvd-transfer-191
dvd-transfer-230
dvd-transfer-46
dvd-transfer-93
TheVistaGroup-1998CBSChristmasCommercials
Muppet_Family_Christmas_ABC_WOC_1988-12-02
a-muppet-family-christmas-1987-full-broadcast-w-ads-savetube.us
1988-11-01-muppet-family-christmas-original-partial-broadcast-with-commercials-katu-2-portland-or
muppets-christmas-special-1988
abc-the-christmas-raccoons
abc-special-cabbage-patch-kids-first-christmas
youtube-nJbsHscd3U8
youtube-yjDKbEhMlx0
youtube--4cLOcxn020
kxlyspokane1980sbroadcasts
hbo-the-nutcracker-december-1984-wkow-abc-the-little-rascals-christmas-special-d
Mickey_Christmas_Carol_NBC_WOC_1988-12-04
mickeyschristmascarolnbcspecialwavytv10airingfromdecember1987
nbc-special-mickeys-christmas-carol-1984
NBC_1984_Christmas_Special_A_Christmas_Dream_WOC
tis-the-season-to-be-smurfy
thetownsantaforgot_201912
80s-christmas-specials-with-commercials
80s-christmas-specials-with-commercials-2
80s-christmas-specials-with-commercials-3
he-man-she-ra-christmas-special-tape-part-2
SmokesVHSTape660
cbswcco112301
wsjv-28-abc-commercial-breaks-christmas-eve-1985
wndu-16-nbc-commercial-breaks-12-12-1988-both-partial-and-complete-breaks
vhs-fb-market-box-2-tape-4-grinch-tnt-broadcast-91-frosty-the-snowman-and-charli
rankinchristmas
flintstone-christmas-charlie-brown-christmas-1993`.split('\n');
const out={};
await Promise.all(ids.map(async id=>{
 const m=await fetch('https://archive.org/metadata/'+id).then(r=>r.json());
 const desc=String(m.metadata.description||'').replace(/<[^>]+>/g,' ');
 let mp4=(m.files||[]).filter(f=>/\.mp4$/i.test(f.name)&&!/thumb|sample/i.test(f.name));
 // drop .ia.mp4 derivative if original of same base exists
 const names=new Set(mp4.map(f=>f.name));
 mp4=mp4.filter(f=>!( /\.ia\.mp4$/i.test(f.name) && [...names].some(n=>n!==f.name && n.replace(/\.(mp4)$/i,'')===f.name.replace(/\.ia\.mp4$/i,''))));
 // if both 'X.mp4' (original) and 'X.ia.mp4' style differ by source, keep originals
 out[id]={c:/commercial|ads\b|\bad breaks|woc/i.test(desc+' '+m.metadata.title)?1:0, files:mp4.map(f=>[f.name, Math.round(+f.length||0), f.source]).sort((a,b)=>a[0].localeCompare(b[0],undefined,{numeric:true}))};
}));
window._files=out;
Object.entries(out).map(([k,v])=>`${k} [c=${v.c}] `+v.files.map(f=>`${f[0]} (${Math.round(f[1]/60)}m,${f[2]})`).join(' ; ')).join('\n')
```

### turn05.txt call 24: mcp__remote-devices__Claude_Browser__javascript_tool
```
const ids=['a-disney-christmas-gift-12-04-1982-walt-disney-cbs','dvd-transfer-191','dvd-transfer-161','dvd-transfer-46','december1991cbsbroadcastofrudolphtherednosedreindeerrecordedoffwtkrtv3','mickeyschristmascarolnbcspecialwavytv10airingfromdecember1987','dvd-transfer-222','80s-christmas-specials-with-commercials-2','80s-christmas-specials-with-commercials-3','youtube--4cLOcxn020'];
const out=[];
for(const id of ids){const m=await fetch('https://archive.org/metadata/'+id).then(r=>r.json()); const d=String(m.metadata.description||'').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
 const hits=[...d.matchAll(/.{0,160}(commercial|ads\b|ad break|WOC).{0,160}/gi)].map(x=>x[0]).slice(0,6);
 out.push('## '+id+'\n'+hits.join('\n  ..')+'\nREVIEWS: '+(m.reviews||[]).map(r=>(r.reviewtitle||'')+': '+String(r.reviewbody||'').slice(0,160)).join(' || '));}
out.join('\n')
```

### turn05.txt call 31: mcp__remote-devices__Claude_Browser__javascript_tool
```
const ids='zVpIKt7wYuU LRcVZi-x3bw gtQJYbTemfo VXiHH4p51Uc K-ThQtxTGZc saiodJr6UR8 Z71ahXqgBTM oF7foUcyhQs u-j7HxI89aM KU4BeYgayXk Nf3l8olHDB4 HzxVPmGwWC8 u3WC_U-rf5A 5ftduLCmk_s vuq99UxjpvA Mbzdx70dkMU VK7zZz0N4NU Im1So5GHeSQ mvqwGvgcDuU 4nak92AJATY OPwTN0zLyC4 DeMVGEd86Qw fev9vp3UcsQ fQaRwV3NM1A pOu70NcoSfw Ggs_txOqT04 noFAmiMg1Kw 7dr15Utx-NM 2qKtdmfTT9Y TtzUkLXE5-g GpdO9Oylw74'.split(' ');
const o={};
await Promise.all(ids.map(async id=>{const h=await fetch('https://www.youtube.com/watch?v='+id).then(r=>r.text()); const m=h.match(/"lengthSeconds":"(\d+)"/); const s=h.match(/"playabilityStatus":\{"status":"(\w+)"/); o[id]=[m?+m[1]:0, s?s[1]:'?'];}));
JSON.stringify(o)
```

### turn05.txt call 32: mcp__remote-devices__Claude_Browser__navigate
```
https://www.youtube.com/
```

### turn05.txt call 33: mcp__remote-devices__Claude_Browser__javascript_tool
```
const ids='zVpIKt7wYuU LRcVZi-x3bw gtQJYbTemfo VXiHH4p51Uc K-ThQtxTGZc saiodJr6UR8 Z71ahXqgBTM oF7foUcyhQs u-j7HxI89aM KU4BeYgayXk Nf3l8olHDB4 HzxVPmGwWC8 u3WC_U-rf5A 5ftduLCmk_s vuq99UxjpvA Mbzdx70dkMU VK7zZz0N4NU Im1So5GHeSQ mvqwGvgcDuU 4nak92AJATY OPwTN0zLyC4 DeMVGEd86Qw fev9vp3UcsQ fQaRwV3NM1A pOu70NcoSfw Ggs_txOqT04 noFAmiMg1Kw 7dr15Utx-NM 2qKtdmfTT9Y TtzUkLXE5-g GpdO9Oylw74'.split(' ');
const o={};
for (const id of ids){const h=await fetch('https://www.youtube.com/watch?v='+id).then(r=>r.text()); const m=h.match(/"lengthSeconds":"(\d+)"/); const s=h.match(/"playabilityStatus":\{"status":"(\w+)"/); o[id]=[m?+m[1]:0, s?s[1]:'?'];}
JSON.stringify(o)
```

### turn05.txt call 34: mcp__remote-devices__Claude_Browser__navigate
```
https://archive.org/
```

### turn05.txt call 35: mcp__remote-devices__Claude_Browser__javascript_tool
```
const ids=`a-magical-disney-christmas-1981-cbs-version youtube-nJbsHscd3U8 a-disney-christmas-gift-12-04-1982-walt-disney-cbs abc-the-christmas-raccoons nbc-special-mickeys-christmas-carol-1984 NBC_1984_Christmas_Special_A_Christmas_Dream_WOC dvd-transfer-222 he-man-and-she-ra-christmas-specail-woc-12-85 charlie-brown-and-frosty-the-snowman-cbs-woc-incomplete-1986-12-12 a-muppet-family-christmas-1987-full-broadcast-w-ads-savetube.us mickeyschristmascarolnbcspecialwavytv10airingfromdecember1987 the-california-raisins-christmas-special-cbs-1987 pee-wees-playhouse-christmas-cbs-12-24-1988 Muppet_Family_Christmas_ABC_WOC_1988-12-02 Mickey_Christmas_Carol_NBC_WOC_1988-12-04 tis-the-season-to-be-smurfy Holiday_Specials_CBS_WOC_1988-11-28 rudolph-the-red-nose-reindeer-1989-cbs-woc december1991cbsbroadcastofrudolphtherednosedreindeerrecordedoffwtkrtv3 xmas921 xmas922 agarfieldchristmas12021992 garfield-christmas-12-14-1994 thetownsantaforgot_201912 kidswbcbs Frosty_Returns_CBS_WOC_1997-12-12 The_Story_Of_Santa_Claus_CBS_WOC_1997-12-12 a-garfield-christmas-1987-wfmy-cbs-2000-airing c-2a-931a-5-aa-61-449d-a-2e-5-1aef-2e-7adf-7e-1 rudolph-the-red-nose-reindeer-cbs-2004-woc FrostyAndFrostyReturnsCBS2004Or2005 80s-christmas-specials-with-commercials 80s-christmas-specials-with-commercials-2 80s-christmas-specials-with-commercials-3 rankinchristmas kxlyspokane1980sbroadcasts dvd-transfer-161 SmokesVHSTape660 a-garfield-christmas-commercial-breaks-dec.-1999-cbs TheVistaGroup-1998CBSChristmasCommercials wndu-16-nbc-commercial-breaks-12-12-1988-both-partial-and-complete-breaks wsjv-28-abc-commercial-breaks-christmas-eve-1985 youtube-yjDKbEhMlx0 youtube--4cLOcxn020`.split(' ');
const out={};
await Promise.all(ids.map(async id=>{const m=await fetch('https://archive.org/metadata/'+id).then(r=>r.json());
 let mp4=(m.files||[]).filter(f=>/\.mp4$/i.test(f.name)&&!/VIDEO_TS\.mp4$/i.test(f.name));
 const names=new Set(mp4.map(f=>f.name));
 mp4=mp4.filter(f=>!(/\.ia\.mp4$/i.test(f.name)&&names.has(f.name.replace(/\.ia\.mp4$/i,'.mp4'))));
 out[id]=mp4.map(f=>[f.name,Math.round(+f.length||0)]);}));
JSON.stringify(out)
```

### turn05.txt call 38: Bash
```
mkdir -p /home/claude/xmas && cat > /home/claude/xmas/build.py <<'EOF'
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
for group,coll,items in (('mn',f'{PREFIX} - Station Breaks (Minnesota: WCCO/KSTP/KARE)',MN),('net',f'{PREFIX} - Station Breaks (Network CBS/ABC/NBC)',NET)):
    for sid,title,net,date,ref in items:
        url,secs,src=ref_url(ref)
        s={'id':sid,'collection':coll,'type':'commercial','slot':title,'network':net,'runtime':dur(secs),'source':src,'url':url,
           'notes':'Commercial/bumper break reel. Page: '+(f'https://archive.org/details/{ref[1]}' if ref[0]=='a' else url)}
        if date: s['broadcast_date']=date; s['year']=int(date[:4])
        streams.append(s)

channel={'channels':[{'number':'1225','name':'Vintage Kids Christmas','group':'Holiday',
  'description':'Children\'s Christmas specials as broadcast on CBS, ABC and NBC (plus WCCO/KSTP/KARE breaks), 1981-2005, from off-air VHS/Beta captures with original commercials, bumpers and station IDs.',
  'enabled':True,'streams':streams}]}
yaml.safe_dump(channel, open(OUT/'channel-1225-vintage-kids-christmas.yaml','w'), sort_keys=False, allow_unicode=True, width=200)

content=[{'key':k,'collection':c,'order':'chronological'} for k,c,_ in prog_keys]
content+= [{'key':'breaks_mn','collection':f'{PREFIX} - Station Breaks (Minnesota: WCCO/KSTP/KARE)','order':'shuffle'},
           {'key':'breaks_net','collection':f'{PREFIX} - Station Breaks (Network CBS/ABC/NBC)','order':'shuffle'}]
seq=[{'key':'break-mn','items':[{'duration':'00:02:00','content':'breaks_mn','filler_kind':'Commercial','trim':True,'discard_attempts':3}]},
     {'key':'break-net','items':[{'duration':'00:02:00','content':'breaks_net','filler_kind':'Commercial','trim':True,'discard_attempts':3}]}]
items=[]
for i,(k,c,slot) in enumerate(prog_keys):
    items.append({'all':k,'custom_title':slot})
    items.append({'sequence':'break-mn' if i%2==0 else 'break-net'})
seq.append({'key':'kids-xmas-channel','items':items})
sched={'name':'1225 Vintage Kids Christmas','description':'Chronological run (1981 -> 2005) of off-air kids Christmas broadcasts; a 2-minute vintage station break (alternating Minnesota and network reels) between programs. Loops.',
       'media':{'preferred_extension':'mp4','mp4_only':True},'content':content,'sequence':seq,'playout':[{'sequence':'kids-xmas-channel'},{'repeat':True}]}
yaml.safe_dump(sched, open(OUT/'schedules'/'1225.yml','w'), sort_keys=False, allow_unicode=True, width=200)

# flat URL list (tab-separated) for anything else
with open(OUT/'urls.tsv','w') as f:
    f.write('id\ttype\tnetwork\tdate\truntime\turl\n')
    for s in streams: f.write(f"{s['id']}\t{s['type']}\t{s['network']}\t{s.get('broadcast_date','')}\t{s['runtime']}\t{s['url']}\n")
print(len(P),'programs,',len(MN)+len(NET),'break reels, total runtime h =',round(sum(1 for _ in [])))
EOF
echo ok
```

### turn05.txt call 47: Bash
```
cd /home/claude/xmas && python3 - <<'EOF'
p='build.py'; s=open(p).read()
old=s[s.index("for group,coll,items in"):s.index("channel={")]
new='''break_keys={'mn':[], 'net':[]}; long_breaks=[]
for group,items in (('mn',MN),('net',NET)):
    for sid,title,net,date,ref in items:
        url,secs,src=ref_url(ref)
        coll=f'{PREFIX} - Break - {title} [{sid}]'
        s={'id':sid,'collection':coll,'type':'commercial','slot':title,'network':net,'runtime':dur(secs),'source':src,'url':url,
           'notes':'Commercial/bumper break reel. Page: '+(f'https://archive.org/details/{ref[1]}' if ref[0]=='a' else url)}
        if date: s['broadcast_date']=date; s['year']=int(date[:4])
        streams.append(s)
        (long_breaks if secs>20*60 else break_keys[group]).append((sid,coll,title))
'''
s=s.replace(old,new)
old2=s[s.index("content=[{'key':k"):s.index("sched={")]
new2='''content=[{'key':k,'collection':c,'order':'chronological'} for k,c,_ in prog_keys]
allbreaks=break_keys['mn']+break_keys['net']+long_breaks
content+=[{'key':k,'collection':c,'order':'chronological'} for k,c,_ in allbreaks]
# round-robin: after each program play ONE short break reel, alternating Minnesota and network reels
mn=break_keys['mn']; nt=break_keys['net']; items=[]; im=inn=0
marathon=[x for x in prog_keys if x[0].startswith('marathon_')]
regular=[x for x in prog_keys if not x[0].startswith('marathon_')]
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
'''
s=s.replace(old2,new2)
s=s.replace("a 2-minute vintage station break (alternating Minnesota and network reels) between programs","one vintage station-break reel (alternating Minnesota WCCO/KSTP/KARE and CBS/ABC/NBC network reels) between programs, then long commercial reels and multi-hour marathon tapes")
s=s.replace("print(len(P),'programs,',len(MN)+len(NET),'break reels, total runtime h =',round(sum(1 for _ in [])))","print(len(P),'programs,',len(MN)+len(NET),'break reels')")
open(p,'w').write(s)
EOF
python3 build.py && cd out && python3 - <<'EOF'
import json,yaml,jsonschema
S='/home/claude/streamtv-source/schemas/'
c=yaml.safe_load(open('channel-1225-vintage-kids-christmas.yaml')); s=yaml.safe_load(open('schedules/1225.yml'))
jsonschema.validate(c,json.load(open(S+'channel.schema.json'))); jsonschema.validate(s,json.load(open(S+'schedule.schema.json'))); print('schemas PASS')
keys={k['key'] for k in s['content']}; used={i.get('all') for q in s['sequence'] for i in q['items']}-{None}
print('refs resolve:',used<=keys, len(keys),'content keys')
EOF
```

### turn05.txt call 60: Bash
```
cd /home/claude/xmas && cat > report.py <<'EOF'
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
EOF
cat > report_template.md <<'EOF'
# Vintage Kids Christmas — StreamTV channel 1225: sources

Researched November 18, 2026 on archive.org and YouTube. Every row links to the page its facts came from.

## Plain-language terms

- **Off-air capture** — a recording someone made at home by taping the TV signal as it aired (VHS or Betamax), later digitized. It shows TV exactly as it was broadcast.
- **Commercials / station breaks** — the ad breaks between program segments. Local stations inserted their own ads, so the same special looks different city to city.
- **Bumpers** — the short "We'll be right back" / "Now back to…" cards and voiceovers on either side of a break.
- **Station identification (ID)** — the local channel's logo or announcement (for example "WCCO 4"). A recording "carries a local identity" when you see the local station rather than only the network.
- **WOC** — "with original commercials". Several uploaders put it in file names. Where WOC is the only evidence, this guide says so.
- **Uploader** — the person or account that posted the item. Following an uploader's page shows everything else they posted.
- **Playlist / collection** — a group of related videos (YouTube) or items (archive.org) you can follow as one set.
- **Tier 1 / Tier 2** — Tier 1 is a strong match: a kids' Christmas program on CBS, ABC or NBC from the 1980s to early 2000s, with commercials confirmed by the description or title. Tier 2 is a partial match: one of those points is missing or unconfirmed.

## Tier 1 — high-confidence matches ({{N1}})

{{TIER1}}

## Tier 2 — partial matches ({{N2}})

{{TIER2}}

## Station-break reels used between programs

The channel plays one of these real break reels between programs, alternating Minnesota and network reels, so the gaps sound like 1980s–90s TV.

### Minnesota (WCCO 4, KSTP 5, KARE 11)

{{MN}}

### Network (CBS, ABC, NBC affiliates elsewhere)

{{NET}}

## Collections and channels worth following

| Collection / channel | Platform | Why it matters | Link |
|---|---|---|---|
| TCMediaNow (Twin Cities Media Now) | YouTube | A Twin Cities non-profit that digitizes local TV. Has the WCCO/CBS breaks from Rudolph, Charlie Brown, Frosty, the Grinch and 'Twas the Night Before Christmas (December 1986), plus KSTP/ABC Christmas spots. Best Minnesota source found. | https://www.youtube.com/@tcmedianow |
| FenwickTV | YouTube | Tape #535: WCCO breaks from Rudolph and Frosty (December 1992), KSTP Christmas ads (December 1992). | https://www.youtube.com/@TVsFenwick |
| tvandmoviearchive | YouTube + archive.org | WCCO, KSTP and KARE commercial reels by date, including WCCO Christmas Day 1995. | https://www.youtube.com/@tvandmoviearchive |
| Smoke's VHS/DVR Collection | archive.org | Minneapolis–St. Paul off-air tapes (KARE, KSTP, WCCO, KMSP), including KSTP Dec 5, 1991 and KARE Thanksgiving 1991. | https://archive.org/details/smokesvhsdvrcollection |
| The VHS Vault | archive.org | The "Vintage VHS vault": 129,000+ items. Sub-collections that matter here: Kid's Shows on VHS, TV Show VHS, Commercials From The Vault. | https://archive.org/details/vhsvault |
| Commercials From The Vault | archive.org | Ad-break reels by station and date (includes the Cleveland WJW/WEWS 1993 holiday promos and bumpers). | https://archive.org/details/vhscommercials |
| @vhs_deck | archive.org | The "… CBS/ABC/NBC WOC 19xx-12-xx" series: Claymation 1987, Muppet Family 1988, Mickey 1988, Frosty Returns 1997, Story of Santa Claus 1997. | https://archive.org/details/@vhs_deck |
| @jacobburkejr (DVD Transfer series) | archive.org | Numbered DVD Transfers of whole tapes, with very detailed notes: #222 (WCBS 1985), #161 (NYC 1986), #190/#191 (Wisconsin 1987/1992), #230 (NYC 1992), #94 (1999). | https://archive.org/details/@jacobburkejr |
| @walt_s_vault_ | archive.org | Disney anthology network broadcasts (A Magical Disney Christmas 1981, A Disney Christmas Gift 1982). | https://archive.org/details/@walt_s_vault_ |
| @takemebacktothe80s | archive.org | 1984 Florida off-air: Christmas Raccoons, Cabbage Patch Kids, Mickey's Christmas Carol. | https://archive.org/details/@takemebacktothe80s |
| The Museum of Classic Chicago Television | YouTube (mirrored on archive.org) | Complete broadcasts with every break itemized (WLS/ABC Santa Claus Is Comin' to Town 1981). Some YouTube originals are no longer playable; the archive.org mirrors still work. | https://www.youtube.com/@FuzzyMemoriesTV |
| Lost Classics from a Xennial Childhood | YouTube | Full 1980s network specials with original breaks (NBC Smurfs 1984, ABC Cabbage Patch 1984). | https://www.youtube.com/@TheXennial |
| Nostalgic Christmas shows with old commercial breaks | YouTube playlist (about 36 videos) | Ready-made playlist of Christmas shows with their breaks. | https://www.youtube.com/playlist?list=PLCremF6kRyQjynqlr73lLAS32HDrETOGU |
| Christmas Commercial Breaks (Retro TV Film and Video!) | YouTube playlist (about 34 videos) | Complete CBS break sets for Rudolph (1990, 1999) and more. | https://www.youtube.com/playlist?list=PLSvjlEPnm7jG8gvHB2sLWPwWJpN3c3N8- |
| Christmas TV Classics (VHS) incl. commercials, Dec 1997 (mike kling) | YouTube playlist (about 37 videos) | A late-90s holiday tape split into parts. | https://www.youtube.com/playlist?list=PLpTpgw8or0jllJgMNwYGBn_xpUKGDZy3o |

## Also found, not loaded into the channel

These are duplicates of something already in the channel, are outside the target, or are too long or mixed to schedule cleanly. Add them by hand if you want them.

- **Duplicate copies**: Claymation Christmas CBS 12/21/1987 ([vhs_deck copy](https://archive.org/details/Claymation_Christmas_Celebration_CBS_WOC_1987-12-21)); Cabbage Patch Kids, ABC 1984 ([partial archive.org copy](https://archive.org/details/abc-special-cabbage-patch-kids-first-christmas)); Muppet Family Christmas 1987 with ads on YouTube ([Stringer's Stuff](https://www.youtube.com/watch?v=2qKtdmfTT9Y), [Nomad Productions](https://www.youtube.com/watch?v=fFqan3_zvuA), [ABC 7 copy](https://www.youtube.com/watch?v=YOtHvFYgq6c)); The Christmas Toy, NYC 12/6/1986 ([VCR Power](https://www.youtube.com/watch?v=7dr15Utx-NM)); A Wish for Wings That Work, CBS 1992 with commercials ([Video Rescue Center](https://www.youtube.com/watch?v=GpdO9Oylw74)); Muppet Family Christmas, KATU 1988 partial ([archive.org](https://archive.org/details/1988-11-01-muppet-family-christmas-original-partial-broadcast-with-commercials-katu-2-portland-or)).
- **Long or mixed tapes**: [Rankin/Bass 7-hour marathon with vintage ads](https://archive.org/details/rankinchristmas) (re-upload; network not stated); [KXLY Spokane (ABC) 1985 tape](https://archive.org/details/kxlyspokane1980sbroadcasts) (about 6 hours; some specials have commercials); [DVD Transfer 161, NYC Dec 1986](https://archive.org/details/dvd-transfer-161); [DVD Transfer 190, WKBT CBS 1987](https://archive.org/details/dvd-transfer-190); [DVD Transfer 191, Wisconsin 1992](https://archive.org/details/dvd-transfer-191); [DVD Transfer 230, NYC 1992](https://archive.org/details/dvd-transfer-230); [DVD Transfer 94, 1999](https://archive.org/details/dvd-transfer-93); [Rudolph 2005 CBS "until 2am"](https://archive.org/details/rudolph-2005-cbs-until-2am) (about 9 hours); [1990 CBS Frosty and Charlie Brown + soaps](https://archive.org/details/vhs-fb-market-box-2-tape-4-grinch-tnt-broadcast-91-frosty-the-snowman-and-charli) (6 hours); [Dec 1984 tape: WKOW/ABC Little Rascals Christmas + WISC/CBS Santa Claus](https://archive.org/details/hbo-the-nutcracker-december-1984-wkow-abc-the-little-rascals-christmas-special-d); [Dec 1989 tape: He-Man & She-Ra special with commercials, Rudolph, Mickey](https://archive.org/details/he-man-she-ra-christmas-special-tape-part-2).
- **Before 1980 (adjacent years)**: [ABC Year Without a Santa Claus, KTXS 12/9/1977, breaks and excerpts](https://archive.org/details/youtube-yjDKbEhMlx0); [NBC A Flintstone Christmas, KRBC 12/7/1977, breaks and excerpts](https://archive.org/details/youtube--4cLOcxn020); [A Cosmic Christmas, Dec 1980 broadcast with commercials](https://www.youtube.com/watch?v=TtzUkLXE5-g) (Canadian special; the airing station is not named).
- **Minnesota, not kids' programming**: [KSTP A Vikings Christmas, 12/25/1989](https://www.youtube.com/watch?v=lh83ojuAkx8); [Christmas Eve (Loretta Young) taped off KARE 12/22/1986 with commercials](https://www.youtube.com/watch?v=jRnizx1E4u8); [WCCO commercials 11/23/2001](https://archive.org/details/cbswcco112301); [KSTP commercials Dec 2006](https://archive.org/details/kstp-commercials-dec06).
- **Not children's**: Dolly Parton Christmas at Home, ABC 1990, with commercials ([archive.org](https://archive.org/details/dolly-parton-christmas-at-home-12-21-1990-with-original-commercials)); Ernest Saves Christmas, ABC 12/11/1993 WOC ([archive.org](https://archive.org/details/Ernest_Saves_Christmas_ABC_WOC_1993-12-11)); A Christmas Carol (1984), CBS 1986 ([archive.org](https://archive.org/details/a-christmas-carol-1984-cbs-broadcast-1986)).

## Search gaps and items that could not be verified

- **KCCO 7 Alexandria**: nothing found on archive.org or YouTube. YouTube searches for "KCCO" return unrelated accounts.
- **WCCO and KSTP full programs**: no complete kids' Christmas special recorded off WCCO or KSTP turned up. Only the break reels in the table above. The channel pairs them with network specials from other cities, so it plays as "Minnesota ads between the shows", not as a true Twin Cities recording. The one local program found is the WCCO Walt Disney World Christmas special (1987, YouTube).
- **"Commercials" based on a label only**: items marked "Likely — WOC label" have no description beyond the title. Check one in a browser before relying on it.
- **Uncertain dates**: the 1984 Smurfs, 1985 WCBS, 1989 and 2003–2004 Rudolph, and 1997 YouTube tape dates are placeholders (marked in each item's notes). Pee-wee's Playhouse is labeled 12-24-1988, but CBS premiered it on 12-21-1988.
- **YouTube reliability**: YouTube videos can disappear or be blocked for copyright at any time. One original (WLS 1981 Santa Claus Is Comin' to Town) is already unplayable on YouTube, so the channel uses the archive.org mirror. Running the install script's URL check before each season catches dead links.
- **GitHub repositories**: the only repository any item mentions is the vhs-decode tool ([github.com/oyvindln/vhs-decode](https://github.com/oyvindln/vhs-decode)), used to digitize one tape (WHBF/WQAD 1996). It is capture software and adds nothing about broadcast dates or networks.
- **StreamTV wiki note**: the wiki describes a `POST /import/validate/channel` route, but the current StreamTV-source code has no such route. Validation runs inside `POST /api/import/channels/yaml?validate=true`, which the script uses.
EOF
python3 report.py && head -c 1500 out/SOURCES.md && grep -c "^| " out/SOURCES.md
```

### turn05.txt call 65: mcp__remote-devices__Claude_Browser__javascript_tool
```
const urls=JSON.parse(`["https://archive.org/download/a-magical-disney-christmas-1981-cbs-version/A%20Magical%20Disney%20Christmas%20-%201981%20CBS%20Version.mp4","https://archive.org/download/NBC_1984_Christmas_Special_A_Christmas_Dream_WOC/VIDEO_TS/VTS_01_1.mp4","https://archive.org/download/dvd-transfer-222/Title%201%20%28Rudolph%20the%20Red-Nosed%20Reindeer%20-%201985%20WCBS%20Recording%29.mp4","https://archive.org/download/mickeyschristmascarolnbcspecialwavytv10airingfromdecember1987/Mickey%27s%20Christmas%20Carol%20%28NBC%20Special%20-%20WAVY-TV%2010%20airing%20from%20December%201987%29.mp4","https://archive.org/download/a-muppet-family-christmas-1987-full-broadcast-w-ads-savetube.us/A%20Muppet%20Family%20Christmas%20%281987%29%20%5BFull%20Broadcast%20wAds%5D%20-%20savetube.us.mp4","https://archive.org/download/thetownsantaforgot_201912/Winnie%20The%20Pooh%20%26%20Christmas%20Too%2C%20The%20Making%20of%20Aladdin%20-%20A%20Whole%20New%20World.mp4","https://archive.org/download/TheVistaGroup-1998CBSChristmasCommercials/1998%20CBS%20Christmas%20Commercials%20%E2%80%A2%2060%20FPS%201998.mp4","https://archive.org/download/SmokesVHSTape660/KSTP-TV%20-%20December%205%2C%201991%20Commercials.mp4","https://archive.org/download/c-2a-931a-5-aa-61-449d-a-2e-5-1aef-2e-7adf-7e-1/c2a931a5-aa61-449d-a2e5-1aef2e7adf7e%20%281%29.mp4"]`);
const out=[];
for(const u of urls){const m=u.match(/download\/([^/]+)\/(.+)$/); const id=m[1], name=decodeURIComponent(m[2]); const md=await fetch('https://archive.org/metadata/'+id).then(r=>r.json()); out.push(((md.files||[]).some(f=>f.name===name)?'OK ':'MISSING ')+id+'/'+name);}
// also range-GET first bytes of two files to prove they stream
out.join('\n')
```

### turn05.txt call 66: mcp__remote-devices__Claude_Browser__javascript_tool
```
const md=await fetch('https://archive.org/metadata/TheVistaGroup-1998CBSChristmasCommercials').then(r=>r.json()); md.files.filter(f=>/mp4|mkv|mov/i.test(f.name)).map(f=>JSON.stringify(f.name)+' '+[...f.name].filter(c=>c.charCodeAt(0)>127).map(c=>c.charCodeAt(0).toString(16)).join(',')+' '+f.source).join('\n')
```

### turn05.txt call 70: mcp__remote-devices__Claude_Browser__javascript_tool
```
const pairs=[["80s-christmas-specials-with-commercials", "80's Christmas Specials with Commercials.mp4"], ["80s-christmas-specials-with-commercials-2", "80's Christmas Specials with Commercials 2.mp4"], ["80s-christmas-specials-with-commercials-3", "80s Christmas Specials with Commercials 3.mp4"], ["FrostyAndFrostyReturnsCBS2004Or2005", "Frosty and Frosty Returns CBS 2004 or 2005.mp4"], ["Frosty_Returns_CBS_WOC_1997-12-12", "Frosty_Returns_CBS_WOC_1997-12-12.mp4"], ["Holiday_Specials_CBS_WOC_1988-11-28", "Holiday_Specials_CBS_WOC_1988-11-28.mp4"], ["Mickey_Christmas_Carol_NBC_WOC_1988-12-04", "Mickey_Christmas_Carol_NBC_WOC_1988-12-04.mp4"], ["Muppet_Family_Christmas_ABC_WOC_1988-12-02", "Muppet_Family_Christmas_ABC_WOC_1988-12-02.mp4"], ["NBC_1984_Christmas_Special_A_Christmas_Dream_WOC", "VIDEO_TS/VTS_01_1.mp4"], ["NBC_1984_Christmas_Special_A_Christmas_Dream_WOC", "VIDEO_TS/VTS_01_2.mp4"], ["SmokesVHSTape660", "KARE - November 28, 1991 Commercials.mp4"], ["SmokesVHSTape660", "KSTP-TV - December 5, 1991 Commercials.mp4"], ["TheVistaGroup-1998CBSChristmasCommercials", "1998 CBS Christmas Commercials • 60 FPS 1998.mp4"], ["The_Story_Of_Santa_Claus_CBS_WOC_1997-12-12", "The_Story_Of_Santa_Claus_CBS_WOC_1997-12-12.mp4"], ["a-disney-christmas-gift-12-04-1982-walt-disney-cbs", "A Disney Christmas Gift (12-04-1982, Walt Disney, CBS).mp4"], ["a-garfield-christmas-1987-wfmy-cbs-2000-airing", "A Garfield Christmas (1987) (WFMY CBS 2000 Airing).mp4"], ["a-garfield-christmas-commercial-breaks-dec.-1999-cbs", "A Garfield Christmas Commercial Breaks (Dec. 1999, CBS).mp4"], ["a-magical-disney-christmas-1981-cbs-version", "A Magical Disney Christmas - 1981 CBS Version.mp4"], ["a-muppet-family-christmas-1987-full-broadcast-w-ads-savetube.us", "A Muppet Family Christmas (1987) [Full Broadcast wAds] - savetube.us.mp4"], ["abc-the-christmas-raccoons", "ABC- The Christmas Raccoons.mp4"], ["agarfieldchristmas12021992", "A Garfield Christmas (12-02-1992).mp4"], ["c-2a-931a-5-aa-61-449d-a-2e-5-1aef-2e-7adf-7e-1", "c2a931a5-aa61-449d-a2e5-1aef2e7adf7e (1).mp4"], ["charlie-brown-and-frosty-the-snowman-cbs-woc-incomplete-1986-12-12", "charlie-brown-and-frosty-the-snowman-cbs-woc-incomplete-1986-12-12.mp4"], ["december1991cbsbroadcastofrudolphtherednosedreindeerrecordedoffwtkrtv3", "December 1991 CBS broadcast of Rudolph the Red-Nosed Reindeer (recorded off WTKR-TV 3).mp4"], ["dvd-transfer-222", "Title 1 (Rudolph the Red-Nosed Reindeer - 1985 WCBS Recording).mp4"], ["dvd-transfer-222", "Title 2 (A Charlie Brown Christmas - 1985 WCBS Recording).mp4"], ["dvd-transfer-222", "Title 3 (Twas the Night Before Christmas - 1985 WCBS Recording).mp4"], ["dvd-transfer-222", "Title 5 (How the Grinch Stole Christmas - 1985 WCBS Recording).mp4"], ["dvd-transfer-222", "Title 6 (Frosty the Snowman - 1985 WCBS Recording).mp4"], ["garfield-christmas-12-14-1994", "Garfield Christmas (12-14-1994).mp4"], ["he-man-and-she-ra-christmas-specail-woc-12-85", "he-man and she-ra christmas specail WOC 12-85.mp4"], ["kidswbcbs", "KIDSWB_CBS.mp4"], ["mickeyschristmascarolnbcspecialwavytv10airingfromdecember1987", "Mickey's Christmas Carol (NBC Special - WAVY-TV 10 airing from December 1987).mp4"], ["nbc-special-mickeys-christmas-carol-1984", "NBC Special- Mickeys Christmas Carol 1984.mp4"], ["pee-wees-playhouse-christmas-cbs-12-24-1988", "Pee Wee's Playhouse Christmas, CBS, 12-24-1988.mp4"], ["rudolph-the-red-nose-reindeer-1989-cbs-woc", "Rudolph The Red Nose Reindeer 1989 CBS woc.mp4"], ["rudolph-the-red-nose-reindeer-cbs-2004-woc", "Rudolph The Red Nose Reindeer CBS 2004 WOC.mp4"], ["the-california-raisins-christmas-special-cbs-1987", "The California Raisins Christmas Special CBS 1987.mp4"], ["thetownsantaforgot_201912", "A Flintstone Family Christmas.mp4"], ["thetownsantaforgot_201912", "The Town Santa Forgot.mp4"], ["thetownsantaforgot_201912", "The Twelve Days of Christmas.mp4"], ["thetownsantaforgot_201912", "The Wish That Changed Christmas.mp4"], ["thetownsantaforgot_201912", "Winnie The Pooh & Christmas Too, The Making of Aladdin - A Whole New World.mp4"], ["tis-the-season-to-be-smurfy", "Tis The Season To Be Smurfy.mp4"], ["wndu-16-nbc-commercial-breaks-12-12-1988-both-partial-and-complete-breaks", "WNDU-16 NBC Commercial Breaks(12 12 1988)(Both partial and complete breaks).mp4"], ["xmas921", "XMAS92_1.mp4"], ["xmas922", "XMAS92_2.mp4"], ["youtube-nJbsHscd3U8", "nJbsHscd3U8.mp4"]];
const cache={}; const miss=[];
for(const [id,n] of pairs){ cache[id]=cache[id]||await fetch('https://archive.org/metadata/'+id).then(r=>r.json()); const f=(cache[id].files||[]).find(f=>f.name===n); if(!f) miss.push(id+'/'+n); else if(!(+f.size>1e6)) miss.push('tiny '+id+'/'+n+' '+f.size); }
`${pairs.length} files checked, ${miss.length} problems`+(miss.length?'\n'+miss.join('\n'):'')
```
