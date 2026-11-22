"""Researched sources for the StreamTV holiday channels.

Program tuple: (sid, title, network_or_station, air_date 'YYYY-MM-DD' or '', year, tier, ads, ref, note)
Break tuple:   (sid, title, network_or_station, air_date or '', ref)
ref: ('a', archive_identifier, filename_or_None) | ('y', youtube_id)
ads: yes | mostly | some | label-only | inferred | unverified | no
Tier 1 = holiday program for kids/families on CBS, ABC or NBC, 1980s-early 2000s, commercials confirmed by
description or title. Tier 2 = partial match (one of those points missing or unconfirmed).
"""

def A(i, f=None): return ('a', i, f)
def Y(i): return ('y', i)

CHANNELS = []

# ------------------------------------------------------------------ HALLOWEEN
CHANNELS.append(dict(
 number='1031', slug='vintage-kids-halloween', name='Vintage Kids Halloween',
 desc="Children's Halloween specials as broadcast on CBS, ABC and NBC (plus WCCO/KSTP breaks), 1979-2002, from off-air VHS/Beta captures with original commercials, bumpers and station IDs.",
 programs=[
  ('grinch_night_wls_1979',"Halloween Is Grinch Night",'ABC / WLS-TV 7 Chicago','1979-10-28',1979,2,'yes',Y('xPSDxfSdRb8'),'Complete broadcast with WLS/ABC IDs, bumpers and breaks (Museum of Classic Chicago TV). 1979 is just before the target era.'),
  ('raggedy_pumpkin_cbs_1980',"Raggedy Ann & Andy in The Pumpkin Who Couldn't Smile",'CBS','1980-10-24',1980,1,'yes',Y('p2bQ2eo2jjE'),'YouTube (Kev The Ripper): 1980 CBS rerun with original commercials.'),
  ('disney_halloween_cbs_1981','A Disney Halloween','CBS (Walt Disney anthology)','1981-10-24',1981,1,'yes',A('1981-a-disney-halloween'),'Description: CBS version with commercials; front and end titles missing.'),
  ('kidding_around_halloween_1982',"Kidding Around - Halloween '82 (local kids show)",'NBC O&O / WMAQ-TV 5 Chicago','1982-10-30',1982,1,'yes',A('youtube-LNbQX3Uvpeo'),'Complete broadcast with station ID, PSAs and promos (Museum of Classic Chicago TV mirror).'),
  ('disney_halloween_treat_cbs_1982',"Disney's Halloween Treat (premiere)",'CBS / WISH-TV 8 Indianapolis','1982-10-30',1982,2,'unverified',A('disneys-halloween-treat-10-30-1982-walt-disney-cbs'),'Betamax off-air recording; description does not say whether commercials are included.'),
  ('kidding_around_halloween_1983',"Kidding Around - Halloween '83 (local kids show)",'NBC O&O / WMAQ-TV 5 Chicago','1983-10-29',1983,1,'yes',A('youtube-iakS-aOAYxw'),'Complete broadcast with PSAs and promos.'),
  ('disney_halloween_treat_cbs_1983',"Disney's Halloween Treat (repeat)",'CBS','1983-10-29',1983,1,'yes',A('1983-disneys-halloween-treat'),'Description: CBS Special airing with the original lead-in and commercials.'),
  ('garfield_great_pumpkin_cbs_1985',"Garfield's Halloween Adventure + It's the Great Pumpkin, Charlie Brown",'CBS','1985-10-30',1985,1,'yes',A('halloween-cartoons-1985'),'Description: 1985 CBS broadcast with commercials. Exact date not stated (placeholder Oct 30).'),
  ('disney_scary_tales_kdka_1985',"Disney's Scary Tales - Halloween night (Wonderful World of Disney)",'CBS / KDKA-TV 2 Pittsburgh','1985-10-31',1985,1,'yes',A('TheVistaGroup-TVCommercials1985October31DisneyHalloweenPittsburghPAKDKACBS'),'The Vista Group: unedited off-air Halloween-night tape with commercials.'),
  ('garfield_halloween_cbs_1986',"Garfield's Halloween Adventure",'CBS','1986-10-23',1986,1,'yes',A('img-0279_202209'),'Description: as aired Oct 23, 1986 with commercials.'),
  ('disney_scary_tales_fox_1987',"Disney's Scary Tales (Wonderful World of Disney)",'Fox','1987-10-25',1987,2,'label-only',A('disneys-scary-tales-of-halloween-fox','Wwod Scary Halloween 10 25 87 On Fox - Copy.mp4'),'Fox, not CBS/ABC/NBC. "WOC" in the title only.'),
  ('pooh_boo_cbs_1996',"Boo to You Too! Winnie the Pooh (premiere)",'CBS','1996-10-25',1996,1,'yes',Y('Q6A-ISuU3sE'),'YouTube: CBS premiere with commercials (same night as the WCCO break reel).'),
  ('pumpkin_pooh_whtm_2002',"It's the Great Pumpkin, Charlie Brown + Boo to You Too! Winnie the Pooh",'ABC / WHTM-TV 27 Harrisburg','2002-10-25',2002,2,'inferred',A('CharlieBrownWinnieThePooh2002'),'Recorded off-air Oct 25, 2002; commercials not stated (61-minute runtime suggests they are in).'),
 ],
 mn=[
  ('wcco_halloween_1996','WCCO/CBS breaks during Great Pumpkin + Boo to You Too (Oct 25, 1996)','CBS / WCCO-TV 4 Minneapolis','1996-10-25',Y('uhORheS2lgA')),
  ('kstp_oct_1996','KSTP-TV commercials (October 1996)','ABC / KSTP-TV 5 Minneapolis','1996-10-15',A('SmokesVHSTape584','October 1996 Commercials.mp4')),
  ('kstp_halloween_1999','KSTP/ABC commercials, Halloween 1999 (during Casper)','ABC / KSTP-TV 5 Minneapolis','1999-10-31',Y('NYoPgXm8VyU')),
 ],
 net=[
  ('wbbm_great_pumpkin_1980','WBBM/CBS Great Pumpkin opening & break (1980)','CBS / WBBM-TV 2 Chicago','1980-10-25',A('youtube-fv7A4B58jZc')),
  ('nbc_halloween_1981','NBC Halloween assorted commercials (Oct 30, 1981)','NBC','1981-10-30',Y('8gE8EzfeIGo')),
  ('casper_halloween_1981_ads','Commercials from Casper Halloween Special (Oct 1981)','NBC','1981-10-30',Y('pbcBoVPx4T0')),
  ('cbs_halloween_1985_ads','CBS 1985 Halloween specials commercials','CBS','1985-10-30',Y('Y5qJ70fkRzA')),
  ('cbs_garfield_cb_1985_breaks','CBS breaks, intros & outros: Garfield & Charlie Brown (1985)','CBS','1985-10-30',Y('q88ekg_6M1k')),
  ('kron_halloween_1986','KRON/NBC commercials, Halloween 1986','NBC / KRON-TV 4 San Francisco','1986-10-31',A('capture-a-2454')),
  ('kptv_disney_1986','Disney Scary Tales / Halloween Hall of Fame breaks (Oct 1986)','KPTV 12 Portland (independent)','1986-10-25',A('october-1986-disney-commercials-ads-promos-kptv-12-portland-oregon-halloween-','October 1986 Disney Commercials Ads Promos KPTV 12 Portland Oregon ( Halloween VHS pt 1 ).mp4')),
  ('kcra_halloween_1988','KCRA/NBC commercials, Halloween 1988','NBC / KCRA-TV 3 Sacramento','1988-10-31',A('capture-a-3997')),
  ('cbs_great_pumpkin_1991','CBS breaks: It\'s the Great Pumpkin, Charlie Brown (1991)','CBS','1991-10-30',Y('iEq29W4eZRM')),
  ('abc_halloween_1995','ABC Halloween bumpers & commercials (Hocus Pocus, 1995)','ABC (Ohio affiliate)','1995-10-30',Y('cv5lHP4vAEY')),
  ('abc_tgif_halloween_1996','ABC TGIF Halloween commercials (WBKO, 1996)','ABC / WBKO 13 Bowling Green','1996-10-25',Y('Zf9cvUlduTM')),
  ('kima_halloween_1999','KIMA/CBS commercials, Halloween 1999','CBS / KIMA-TV 29 Yakima','1999-10-31',A('capture-a-3384')),
 ]))

# ------------------------------------------------------------------ THANKSGIVING
M = []   # Macy's parades, one per year
def mp(year, date, ref, ads, tier, note, net='NBC'):
    M.append((f'macys_parade_{year}', f"Macy's Thanksgiving Day Parade {year}", net, date, int(str(year)[:4]), tier, ads, ref, note))
mp(1939,'1939-11-23',A('MacysThanksgivingDayParadeNewYork1939'),'no',2,'Silent home-movie footage (4 min), not a broadcast. Earliest footage found.', net='Home movie (no network)')
mp(1959,'1959-11-26',A('the_33rd_annual_macys_thanksgiving'),'label-only',2,'NBC telecast, 60 min; "WOC" label only. Outside the target era.')
mp('1965-69','1966-11-24',Y('eM-rVUCoR0s'),'no',2,'Partial NBC coverage footage from 1965, 1966 and 1969 (11 min). Outside the target era.')
mp(1968,'1968-11-28',Y('MQJimI8awzM'),'unverified',2,'Partial, 19 min. Outside the target era.')
mp(1972,'1972-11-23',A('youtube-jywap-TwgNk'),'unverified',2,'Restored, 61 min of the broadcast (partial). Outside the target era.')
mp(1976,'1976-11-25',Y('twHX3Pb501g'),'unverified',2,'50th parade, described as complete (119 min).')
mp(1977,'1977-11-24',Y('84ZlEXqGBVk'),'unverified',2,'Incomplete NBC telecast, 21 min.')
mp(1978,'1978-11-23',Y('Ehk5cfEEzfU'),'unverified',2,"CBS's coverage of the Macy's parade (Linda Lavin, Ron Leibman), 23 min.", net='CBS')
mp(1979,'1979-11-22',Y('SWHsL73txG4'),'unverified',2,'Restored partial, 34 min.')
mp(1980,'1980-11-27',A('1980-macys-parade-title-1-te-nos'),'label-only',1,'WNBC; "WOC" label (125 min).')
mp(1981,'1981-11-26',A('macysthanksgivingdayparade1981reuploadwithcommericals'),'yes',1,'Title: with commercials (204 min).')
mp(1982,'1982-11-25',A('macys-parade-1982-nbc_202207'),'inferred',1,'Full NBC telecast, 179 min (a 3-hour runtime suggests commercials are in).')
mp('1983 (Part 1)','1983-11-24',Y('eQDi_1wlQ_M'),'inferred',1,'Part 1 of 2; both parts total about 2 h 55 min.')
mp('1983 (Part 2)','1983-11-24',Y('IWhYO9fTrtI'),'inferred',1,'Part 2 of 2.')
mp(1984,'1984-11-22',Y('aphgFPsN5QI'),'inferred',1,'172 min.')
mp(1985,'1985-11-28',Y('1P7ZLLE0Zx0'),'inferred',1,'180 min.')
mp(1986,'1986-11-27',A('macysthanksgivingdayparade1986full'),'no',2,'Full parade, 146 min; commercials appear to be removed (runtime).')
mp(1987,'1987-11-26',A('1987-macys-parade-full-te-nos'),'label-only',1,'Complete parade, WOC; the same tape continues into a partial NFL game and A Woman of Substance (4 h 12 min).')
mp(1988,'1988-11-24',A('macysthanksgivingdayparade1988withcommercialsvhs_201912'),'yes',1,'WNBC New York with commercials (178 min).', net='NBC / WNBC-TV 4 New York')
mp(1989,'1989-11-23',A('1989_20201225'),'yes',1,'Description: full parade, includes commercials.')
mp(1990,'1990-11-22',Y('IaKxiEs_AeA'),'yes',1,'WLUK Green Bay with commercials (177 min).', net='NBC / WLUK-TV 11 Green Bay')
mp(1991,'1991-11-28',A('untitled16_201912'),'no',2,'Full parade, 146 min; commercials appear removed (runtime). The KARE break reel from this morning is in the break rotation.')
mp(1992,'1992-11-26',A('1992_20201225'),'no',2,'Description: full parade, no commercials.')
mp(1993,'1993-11-25',A('videoplayback2_20191225'),'no',2,'Full parade, 141 min; commercials appear removed.')
mp(1994,'1994-11-24',A('videoplayback3_20191225_1243'),'no',2,'Full parade, 139 min; commercials appear removed.')
mp(1995,'1995-11-23',A('videoplayback4_20191225'),'no',2,'Full parade, 139 min; commercials appear removed.')
mp(1996,'1996-11-28',A('final_20221116'),'inferred',1,'Recorded off WBIR Knoxville; 180 min.', net='NBC / WBIR-TV 10 Knoxville')
mp(1997,'1997-11-27',A('macysthanksgivingdayparade1997full'),'no',2,'Full parade, 139 min; commercials appear removed.')
mp(1998,'1998-11-26',A('untitled17_201912'),'unverified',2,'160 min.')
mp(1999,'1999-11-25',A('videoplayback7_20191226'),'no',2,'Full parade, 137 min; commercials appear removed.')
mp(2000,'2000-11-23',A('macysthanksgivingdayparade2000'),'no',2,'Full parade, 138 min.')
mp(2001,'2001-11-22',A('videoplayback8_20191227'),'no',2,'75th parade, 136 min.')
mp(2002,'2002-11-28',Y('vC_URrUuzto'),'yes',1,'YouTube: full broadcast with commercials.')
mp(2003,'2003-11-27',A('videoplayback-13_202202'),'inferred',1,'181 min.')
mp(2004,'2004-11-25',Y('1tdgQrDr6GA'),'yes',1,'YouTube: full broadcast with commercials.')
mp(2005,'2005-11-24',A('2005-macys-parade'),'no',2,'Complete NBC telecast, 130 min.')
mp(2006,'2006-11-23',A('2006-macy'),'unverified',2,'165 min.')
mp(2007,'2007-11-22',A('videoplayback14_20191229'),'no',2,'130 min.')
mp(2008,'2008-11-27',A('videoplayback15_20191229'),'no',2,'130 min.')
mp(2009,'2009-11-26',A('macys-thanksgiving-day-parade-2009-nbc'),'no',2,'130 min. Outside the target era.')
mp(2010,'2010-11-25',A('macys-thanksgiving-day-parade-2010-nbc'),'no',2,'130 min. Outside the target era.')
mp(2011,'2011-11-24',A('macys-thanksgiving-day-parade-2011-nbc'),'no',2,'130 min. Outside the target era.')
mp(2012,'2012-11-22',A('entire2012macysthanksgivingdayparade'),'no',2,'129 min. Outside the target era.')
mp(2013,'2013-11-28',A('macys-thanksgiving-day-parade-2013-nbc'),'no',2,'129 min. Outside the target era.')
mp(2014,'2014-11-27',A('videoplayback16_20191231'),'no',2,'126 min. Outside the target era.')
mp(2015,'2015-11-26',A('macysparade2015NBC'),'no',2,'129 min. Outside the target era.')
mp('2015 (CBS)','2015-11-26',A('2015-macys-thanksgiving-parade-on-cbs'),'no',2,"CBS's own coverage of the Macy's parade, 118 min.", net='CBS')
mp(2016,'2016-11-24',A('macysparade2016'),'no',2,'128 min. Outside the target era.')
mp(2017,'2017-11-23',Y('rYyUYZjo2IU'),'no',2,'128 min. Outside the target era.')
mp(2018,'2018-11-22',A('2018-macys-thanksgiving-day-parade-full'),'no',2,'129 min. Outside the target era.')
mp(2019,'2019-11-28',Y('BIXmZ48Iww8'),'no',2,'128 min. Outside the target era.')
mp(2020,'2020-11-26',A('the-94th-annual-macys-thanksgiving-day-parade'),'no',2,'Reimagined 2020 parade, 127 min. Outside the target era.')
mp(2021,'2021-11-25',Y('JCyHFuy0YyE'),'inferred',2,'177 min. Outside the target era.')
mp(2022,'2022-11-24',A('2022-macys-thanksgiving-day-parade'),'inferred',2,'180 min. Outside the target era.')
mp(2023,'2023-11-23',Y('w2lhI0C7HuE'),'yes',2,'YouTube: full with commercials. Outside the target era.')
mp(2024,'2024-11-28',A('nbcs-macys-thanksgiving-day-parade-2024','20241128-082900-KGW-1.fix.mp4'),'inferred',2,'Off-air from KGW Portland (214 min). Outside the target era.', net='NBC / KGW-TV 8 Portland')
mp(2025,'2025-11-27',A('macys-2025'),'unverified',2,'5 h 32 min file; likely includes pre- or post-parade coverage. Outside the target era.')

CBSP = [
 ('cbs_all_american_parade_1982','CBS All-American Thanksgiving Day Parade 1982 (excerpts & breaks)','CBS / WBBM-TV 2 Chicago','1982-11-25',1982,1,'yes',Y('OdZmf8tG33g'),'Excerpts plus every surviving break (Museum of Classic Chicago TV).'),
 ('cbs_all_american_parade_1984','CBS All-American Thanksgiving Day Parade 1984 (partial)','CBS / WSAW-TV 7 Wausau','1984-11-22',1984,1,'yes',Y('Trx1z94K9zg'),'Partial, with commercials (37 min).'),
 ('cbs_all_american_parade_1985','CBS All-American Thanksgiving Day Parade 1985','CBS / WBAY-TV 2 Green Bay','1985-11-28',1985,2,'some',Y('1X_qGKyiZJE'),'Description: commercials mostly cut; some intact.'),
 ('cbs_all_american_parade_1986','CBS All-American Thanksgiving Day Parade 1986','CBS / WBAY-TV 2 Green Bay','1986-11-27',1986,1,'yes',Y('ZmymvDNZHRc'),'With commercials (91 min).'),
 ('cbs_all_american_parade_1992','CBS All-American Thanksgiving Parade 1992 (most)','CBS','1992-11-26',1992,2,'unverified',Y('jubxPwejnHw'),'Most of the coverage (168 min).'),
 ('cbs_all_american_parade_1997','CBS All-American Thanksgiving Parade 1997','CBS','1997-11-27',1997,2,'inferred',A('1997-cbs-all-american-thanksgiving-parade'),'179 min.'),
 ('cbs_all_american_parade_1998','CBS All-American Thanksgiving Parade 1998','CBS / WWL-TV 4 New Orleans','1998-11-26',1998,2,'inferred',Y('4pg8k0vVIHI'),'178 min, recorded off WWL.'),
 ('cbs_all_american_parade_2001','CBS All-American Thanksgiving Parade 2001','CBS / WWL-TV 4 New Orleans','2001-11-22',2001,2,'inferred',Y('rmJ8nZEZcfE'),'179 min, recorded off WWL.'),
]

CHANNELS.append(dict(
 number='1128', slug='vintage-kids-thanksgiving', name='Vintage Kids Thanksgiving',
 desc="Thanksgiving specials and every Macy's Thanksgiving Day Parade broadcast found (1939-2025, plus CBS All-American parades), from off-air captures, many with original commercials. WCCO/KARE breaks in rotation.",
 programs=[
  ('berenstain_bigpaw_nbc_1980','The Berenstain Bears Meet Bigpaw','NBC','1980-11-20',1980,2,'unverified',A('youtube-ruQozkxioKg'),'Complete NBC Thanksgiving special; commercials not stated.'),
  ('turkey_caper_1985','The Turkey Caper','Syndicated (original airing)','1985-11-09',1985,2,'unverified',A('the_turkey_caper'),'"Original airing"; network/station and commercials not stated.'),
  ('garfield_thanksgiving_cbs_1989',"Garfield's Thanksgiving (premiere) + Bugs Bunny's Thanksgiving Diet",'CBS','1989-11-22',1989,2,'inferred',A('cbs-thanksgiving-day-nov-22nd-1989-garfield-thanksgiving-bugs-bunny-thanksgiving'),'CBS broadcast Nov 22, 1989, through the President\'s Thanksgiving address (75 min); commercials not stated. WCCO breaks from this night are in the rotation.'),
  ('thanksgiving_almost_wasnt_cn_1998',"The Thanksgiving That Almost Wasn't",'Cartoon Network','1998-11-26',1998,2,'unverified',Y('-BDbjGoV8HY'),'Cable airing, not CBS/ABC/NBC.'),
  ('marathon_1984_tape','Nov-Dec 1984 tape: A Charlie Brown Thanksgiving (partial), Rudolph, Rainbow Brite & more','Not stated','1984-11-21',1984,2,'yes',A('1984-tv-shows-with-commercials-charlie-brown-thanksgiving-partial-rudolf-the-red'),'Title: with commercials; mixed 3 h 23 min tape.'),
 ] + M + CBSP,
 mn=[
  ('wcco_nov22_1989','WCCO breaks during Garfield\'s Thanksgiving & Bugs Bunny\'s Thanksgiving Diet (Nov 22, 1989)','CBS / WCCO-TV 4 Minneapolis','1989-11-22',Y('U0nkV-d5qI4')),
  ('wcco_thanksgiving_1994_p1','WCCO/CBS commercials, Thanksgiving 1994 (part 1)','CBS / WCCO-TV 4 Minneapolis','1994-11-24',Y('6umWySbnDkE')),
  ('wcco_thanksgiving_1994_p2','WCCO/CBS commercials, Thanksgiving 1994 (part 2)','CBS / WCCO-TV 4 Minneapolis','1994-11-24',Y('WrUQyzqET9U')),
  ('kare_nov19_1990','KARE-11/NBC commercials (Nov 19, 1990)','NBC / KARE 11 Minneapolis','1990-11-19',Y('FUokPHGUFTo')),
  ('kare_macys_1991','KARE commercials during the 65th Macy\'s Parade (Nov 28, 1991)','NBC / KARE 11 Minneapolis','1991-11-28',A('SmokesVHSTape660','KARE - November 28, 1991 Commercials.mp4')),
  ('wcco_thanksgiving_1996','WCCO/CBS commercials, Thanksgiving 1996','CBS / WCCO-TV 4 Minneapolis','1996-11-28',Y('UIEY0AXRLJU')),
 ],
 net=[
  ('knbc_kabc_1972_macys','KNBC-4 / KABC-7 commercials & Macy\'s parade (1972)','NBC / KNBC-TV 4 Los Angeles','1972-11-23',Y('qiqhuOoTmwE')),
  ('wkbt_cb_thanksgiving_1987','WKBT/CBS breaks: A Charlie Brown Thanksgiving (Nov 1987)','CBS / WKBT-TV 8 La Crosse','1987-11-24',Y('5cmrXZeQW7k')),
  ('cbs_nov26_1987','CBS commercials, Thanksgiving 1987 (KWTV)','CBS / KWTV 9 Oklahoma City','1987-11-26',Y('1dUI2_saQVE')),
  ('kcra_macys_1988','KCRA/NBC commercials during the Macy\'s Parade (1988)','NBC / KCRA-TV 3 Sacramento','1988-11-24',A('capture-a-4567')),
  ('kjeo_cbs_parade_1988','KJEO/CBS commercials during the All-American Parade (1988)','CBS / KJEO 47 Fresno','1988-11-24',A('capture-a-4585')),
  ('cbs_mayflower_voyagers_1988','CBS breaks: This Is America, Charlie Brown - The Mayflower Voyagers (1988)','CBS','1988-10-21',Y('dezQXWP9tdo')),
  ('cbs_nov22_1989','CBS Thanksgiving specials commercials (Nov 22, 1989, WTKR)','CBS / WTKR-TV 3 Norfolk','1989-11-22',Y('t_qti0a_o-o')),
  ('whio_thanksgiving_1991','WHIO/CBS commercial breaks, Thanksgiving 1991','CBS / WHIO-TV 7 Dayton','1991-11-28',A('whio-7-cbs-commercial-breaks-thanksgiving-1991-mostly-sears-ads')),
  ('whbf_thanksgiving_1992','WHBF/CBS breaks during Daffy Duck, Charlie Brown & Garfield Thanksgiving specials (1992)','CBS / WHBF-TV 4 Rock Island','1992-11-25',A('whbf-4-cbs-commercial-breaks-thanksgiving-1992')),
  ('wood_thanksgiving_1993','WOOD/NBC commercial breaks, Thanksgiving 1993','NBC / WOOD-TV 8 Grand Rapids','1993-11-25',A('wood-8-nbc-commercial-breaks-thanksgiving-1993-mostly-sears-ads')),
  ('wthr_thanksgiving_2002','WTHR/NBC commercial breaks, Thanksgiving 2002','NBC / WTHR 13 Indianapolis','2002-11-28',A('wthr-13-nbc-commercial-breaks-thanksgiving-2002')),
  ('parade_commercials_1990s','1990s commercials aired during the Thanksgiving parade (compilation)','NBC (various years)','1995-11-23',Y('dbj3-1H575I')),
 ]))

# ------------------------------------------------------------------ EASTER
CHANNELS.append(dict(
 number='401', slug='vintage-kids-easter', name='Vintage Kids Easter',
 desc="Easter specials and Walt Disney World Happy Easter Parades as broadcast on ABC, CBS and NBC, 1978-2004, from off-air captures, some with original commercials.",
 programs=[
  ('easter_beagle_wtop_1978',"It's the Easter Beagle, Charlie Brown + The First Easter Rabbit",'CBS / WTOP-TV 9 Washington','1978-03-19',1978,2,'yes',A('1978.03.19-wtop-its-the-easter-beagle-charlie-brown-the-first-easter-rabb',"1978.03.19 - WTOP - It's the Easter Beagle, Charlie Brown, The First Easter Rabbit - WJZ - 1978.04.29 - The Muppet Show - Episode 214 with Elton John - 1978.11.09 - The Muppet Show - Episode 324 with Cheryl Ladd2.mp4"),'Description: with commercials. The title also lists two 1978 Muppet Show episodes (WJZ), but the file is only 55 min, so it most likely holds just the two Easter specials. 1978 is just before the target era.'),
  ('cbs_easter_parade_1987','The 3rd Annual CBS Easter Parade','CBS','1987-04-19',1987,2,'unverified',A('cbs-easter-parade'),'CBS broadcast; commercials not stated. Easter Sunday date inferred.'),
  ('wdw_easter_parade_1987','Walt Disney World Happy Easter Parade 1987','ABC','1987-04-19',1987,2,'inferred',A('wdw-happy-easter-parade-1987'),'ABC broadcast, 68 min (runtime suggests commercials). Easter Sunday date inferred.'),
  ('wdw_easter_parade_1988','Walt Disney World Happy Easter Parade 1988','ABC','1988-04-03',1988,2,'unverified',Y('0pt_6pCGbk4'),'RetroWDW (Lake Buena Vista Historical Society archive), 88 min.'),
  ('wdw_easter_parade_1989','Walt Disney World Happy Easter Parade 1989','ABC','1989-03-26',1989,2,'unverified',Y('IhdGSAvITOA'),'RetroWDW, 81 min.'),
  ('wdw_easter_parade_1991','Walt Disney World Happy Easter Parade 1991','ABC','1991-03-31',1991,2,'unverified',Y('6Sod6NGIy0I'),'RetroWDW, 45 min. The WLS/ABC breaks from this parade are in the rotation.'),
  ('wdw_easter_parade_1992','Walt Disney World Easter Parade 1992','ABC','1992-04-19',1992,1,'yes',A('1992-walt-disney-world-easter-parade-with-commercials'),'Title: with commercials.'),
  ('wdw_easter_parade_1994','Walt Disney World Happy Easter Parade 1994','ABC','1994-04-03',1994,2,'unverified',Y('GNOB5g6sWHI'),'RetroWDW, 46 min.'),
  ('wdw_easter_parade_1995','Walt Disney World Happy Easter Parade 1995','ABC','1995-04-16',1995,2,'unverified',Y('CAe1K9-TE1g'),'RetroWDW, 59 min.'),
  ('wdw_easter_parade_1996','Walt Disney World Happy Easter Parade 1996','ABC / WTVG-TV 13 Toledo','1996-04-07',1996,1,'yes',A('ta-3-estrprd-dis','TA_3_estrprd_dis.mp4'),'1996 VHS tape "with commercials" (WTVG ABC 13 / WTOL CBS 11).'),
  ('wdw_easter_parade_1997','Walt Disney World Happy Easter Parade 1997','ABC','1997-03-30',1997,2,'unverified',A('1997-walt-disney-world-happy-easter-parade-abc'),'59 min.'),
  ('wdw_easter_parade_1999','Walt Disney World Happy Easter Parade 1999','ABC','1999-04-04',1999,2,'unverified',Y('vSnT3_bL3y4'),'RetroWDW, 59 min.'),
  ('easter_bunny_abcfamily_2004',"The Easter Bunny Is Comin' to Town + The First Easter Rabbit",'ABC Family','2004-04-10',2004,2,'yes',A('easter-bunny-is-coming-to-town-the-first-easter-rabbit'),'Title: ABC Family airing with commercials (cable).'),
 ],
 mn=[],
 net=[
  ('cbs_easter_beagle_1978_breaks',"CBS bumper & commercials: It's the Easter Beagle, Charlie Brown (1978)",'CBS','1978-03-19',Y('9UICBKuDZtg')),
  ('komo_easter_1986','KOMO/ABC commercials, Easter 1986','ABC / KOMO-TV 4 Seattle','1986-03-30',A('capture-a-6272')),
  ('kabc_easter_1989','KABC/ABC commercials, Easter 1989','ABC / KABC-TV 7 Los Angeles','1989-03-26',A('capture-a-1992')),
  ('wls_easter_1991','WLS/ABC breaks during the Walt Disney World Happy Easter Parade (1991)','ABC / WLS-TV 7 Chicago','1991-03-31',A('wls-7-abc-commercial-breaks-easter-1991')),
  ('wkjg_easter_1992','WKJG/NBC commercial breaks, Easter 1992','NBC / WKJG-TV 33 Fort Wayne','1992-04-19',A('wkjg-33-nbc-commercial-breaks-easter-1992')),
  ('kima_easter_1994','KIMA/CBS commercials, Easter 1994','CBS / KIMA-TV 29 Yakima','1994-04-03',A('capture-a-3232')),
 ]))

# ------------------------------------------------------------------ VALENTINE'S DAY
CHANNELS.append(dict(
 number='214', slug='vintage-kids-valentines', name="Vintage Kids Valentine's Day",
 desc="Valentine's Day specials from CBS, ABC and NBC (1979-2005) with original commercials and break reels, including WCCO and KARE.",
 programs=[
  ('cathys_valentine_cbs_1989',"Cathy's Valentine",'CBS','1989-02-10',1989,2,'yes',Y('p1laNLcapEg'),'Full special with commercials. Animated, but made for adults more than kids.'),
  ('mickey_valentine_nbc_1989',"Mickey's Happy Valentine Special (Magical World of Disney)",'NBC','1989-02-12',1989,1,'yes',A('mickeys-happy-valentine-special-1989'),'Description: 1989 with commercials.'),
  ('pooh_valentine_abc_2005',"Winnie the Pooh: A Valentine for You",'ABC','2005-02-13',2005,2,'unverified',Y('qzTE8-jV9ms'),'ABC airing Feb 13, 2005; commercials not stated.'),
 ],
 mn=[
  ('wcco_feb_1995','CBS/WCCO commercials (February 1995)','CBS / WCCO-TV 4 Minneapolis','1995-02-12',Y('90ewhGJ9GXA')),
  ('kare_feb_1997','KARE commercials (Feb 23, 1997)','NBC / KARE 11 Minneapolis','1997-02-23',A('SmokesVHSTape584','KARE - February 23, 1997 Commercials.mp4')),
 ],
 net=[
  ('wbbm_be_my_valentine_1979','WBBM/CBS: Be My Valentine, Charlie Brown - opening & break (1979)','CBS / WBBM-TV 2 Chicago','1979-02-14',Y('ewu9MJw6WDU')),
  ('cbs_bugs_valentine_1984','CBS Bugs Bunny Valentine special break (Feb 1984)','CBS','1984-02-14',Y('Fux3t2oBEnM')),
  ('nbc_cbs_sat_morning_feb_1985','NBC & CBS Saturday morning commercials (Feb 9, 1985)','NBC / KPRC + CBS / KHOU Houston','1985-02-09',Y('OCCPQq5Hjpw')),
  ('wcbs_feb10_1989','WCBS breaks during This Is America, Charlie Brown & Cathy\'s Valentine (Feb 10, 1989)','CBS / WCBS-TV 2 New York','1989-02-10',Y('LHfvMh8XF0I')),
  ('nbc_mickey_valentine_bumper_1989','NBC bumper: Mickey\'s Happy Valentine Special (1989)','NBC','1989-02-12',A('the-magical-world-of-disney-mickeys-happy-valentine-special-nbc-bumper-1989')),
  ('nbc_mickey_valentine_break_1989','Commercial break during Mickey\'s Happy Valentine Special (Feb 12, 1989)','NBC (affiliate)','1989-02-12',Y('_ezdJqN7dg8')),
  ('abc_pooh_valentine_1999','ABC intro & bumpers: Winnie the Pooh - A Valentine for You (1999)','ABC','1999-02-13',Y('E0HCyANMIH0')),
  ('abc_pooh_valentine_2001','ABC breaks: Winnie the Pooh - A Valentine for You (2001)','ABC','2001-01-09',Y('30JSZZRNMPM')),
 ]))

# ------------------------------------------------------------------ NEW YEAR'S
CHANNELS.append(dict(
 number='101', slug='vintage-new-years', name="Vintage New Year's",
 desc="New Year's broadcasts: Tournament of Roses Parades (CBS, NBC), Dick Clark's New Year's Rockin' Eve (ABC) and Rudolph's Shiny New Year, 1981-2005, with original commercials and breaks.",
 programs=[
  ('rockin_eve_1981',"Dick Clark's New Year's Rockin' Eve '82",'ABC','1981-12-31',1981,2,'yes',A('new-years-rockin-eve-82'),'Description: contains original commercials. Not a kids program.'),
  ('rose_parade_cbs_1985','Tournament of Roses Parade 1985','CBS / WBAY-TV 2 Green Bay','1985-01-01',1985,1,'yes',Y('eQyZyneDtMU'),'With commercials (some tape issues).'),
  ('rockin_eve_1985',"Dick Clark's New Year's Rockin' Eve 1985-86",'ABC / WGHP 8 Greensboro','1985-12-31',1985,2,'inferred',Y('1kFJ1XTPnxA'),'Full broadcast from VHS (90 min). Not a kids program.'),
  ('rockin_eve_1987',"Dick Clark's New Year's Rockin' Eve (1987)",'ABC','1987-12-31',1987,2,'unverified',Y('L-FyPuhAm1I'),'66 min; year label only. Not a kids program.'),
  ('rose_parade_nbc_1988','Tournament of Roses Parade 1988','NBC / WLUK-TV 11 Green Bay','1988-01-01',1988,1,'yes',Y('lXe0aBmpmc8'),'With commercials (93 min).'),
  ('rose_parade_nbc_1990','101st Tournament of Roses Parade 1990','NBC','1990-01-01',1990,2,'unverified',Y('f7vPEOoVEWo'),'NBC coverage plus short bonus CBS and Univision segments (127 min).'),
  ('rose_parade_cbs_1997','108th Tournament of Roses Parade 1997','CBS','1997-01-01',1997,2,'unverified',A('20250412_20250412_1738'),'Full parade, then 6.5 min of the Cotton Bowl. The title says January 2, 1997.'),
  ('rose_parade_ktla_2000','Rose Parade 2000 (Y2K)','KTLA 5 Los Angeles (independent/WB)','2000-01-01',2000,2,'inferred',A('offairvault-roseparade-ktla-2000-y2k-007'),'Off-air VHS (4 h 5 min).'),
  ('rudolph_shiny_abcfamily_2005',"Rudolph's Shiny New Year",'ABC Family','2005-12-28',2005,2,'yes',A('rudolphsshinynewyearrankinbassproductions1976'),'ABC Family airing with commercials, recorded around December 2005 (cable).'),
 ],
 mn=[],
 net=[
  ('wbo_happy_new_year_cb_1986','CBS breaks: Happy New Year, Charlie Brown (Jan 1, 1986, WBOC)','CBS / WBOC-TV 16 Salisbury','1986-01-01',Y('r3XG_AakfqI')),
  ('cbs_hnycb_1987_p1','CBS breaks: Happy New Year, Charlie Brown (1987) part 1','CBS','1987-01-01',Y('xIeBsy0j5J4')),
  ('cbs_hnycb_1987_p2','CBS breaks: Happy New Year, Charlie Brown (1987) part 2','CBS','1987-01-01',Y('JevHor29boA')),
  ('cbs_hnycb_1987_p3','CBS breaks: Happy New Year, Charlie Brown (1987) part 3','CBS','1987-01-01',Y('r1iN_L3LWL4')),
  ('cbs_hnycb_1987_p4','CBS breaks: Happy New Year, Charlie Brown (1987) part 4','CBS','1987-01-01',Y('UY0Uu5ujY-I')),
  ('wsbt_nyd_1986','WSBT/CBS commercial breaks, New Year\'s Day 1986','CBS / WSBT-TV 22 South Bend','1986-01-01',A('wsbt-22-cbs-commercial-breaks-new-years-day-1986')),
  ('wnyw_rudolph_shiny_1986','WNYW break: Rudolph\'s Shiny New Year (Dec 1986)','WNYW 5 New York (Fox)','1986-12-31',Y('eJveOReJtMk')),
  ('kgtv_rockin_eve_1986','KGTV/ABC commercials during New Year\'s Rockin\' Eve (Dec 31, 1986)','ABC / KGTV 10 San Diego','1986-12-31',Y('Le_gBeDbqoQ')),
  ('kcbs_nyd_1988','KCBS/CBS commercials, New Year\'s Day 1988 (with Happy New Year, Charlie Brown promo)','CBS / KCBS-TV 2 Los Angeles','1988-01-01',A('capture-a-728')),
  ('king_nyd_1989','KING/NBC commercials, New Year\'s Day 1989','NBC / KING-TV 5 Seattle','1989-01-01',A('capture-a-6603')),
  ('cbs_rose_parade_1989','CBS Tournament of Roses commercials (1989)','CBS','1989-01-01',Y('TbRvTQFspzU')),
  ('wndu_nyd_1989','WNDU/NBC commercial breaks, New Year\'s Day 1989','NBC / WNDU-TV 16 South Bend','1989-01-01',A('wndu-16-nbc-commercial-breaks-new-years-day-1989')),
  ('wsbt_nyd_1993','WSBT/CBS commercial breaks, New Year\'s Day 1993','CBS / WSBT-TV 22 South Bend','1993-01-01',A('wsbt-22-cbs-commercial-breaks-new-years-day-1993')),
  ('kndo_nye_1994','KNDO/NBC commercials, New Year\'s Eve 1994','NBC / KNDO 23 Yakima','1994-12-31',A('capture-a-6585')),
  ('kima_nyd_1995','KIMA/CBS commercials, New Year\'s Day 1995','CBS / KIMA-TV 29 Yakima','1995-01-01',A('capture-a-963')),
  ('kmgh_nye_1995','KMGH/ABC commercials, New Year\'s Eve 1995','ABC / KMGH-TV 7 Denver','1995-12-31',A('capture-a-3674')),
 ]))

# ------------------------------------------------------------------ FOURTH OF JULY
CHANNELS.append(dict(
 number='704', slug='vintage-fourth-of-july', name='Vintage Fourth of July',
 desc="Fourth of July broadcasts: ABC's 1986 Liberty Weekend coverage and Macy's fireworks, with original commercials, bumpers and holiday station IDs.",
 programs=[
  ('liberty_opening_abc_1986','Liberty Weekend: Opening Ceremonies','ABC','1986-07-03',1986,2,'unverified',Y('00l8CNcDo9U'),'2 h 40 min; commercials not stated. Family program, not a kids special.'),
  ('liberty_july4_abc_1986','Liberty Weekend: July 4, 1986','ABC','1986-07-04',1986,2,'unverified',Y('alyvheAnNoc'),'1 h 57 min; commercials not stated.'),
  ('liberty_with_ads_abc_1986','Liberty Weekend broadcast with commercials','ABC','1986-07-05',1986,1,'yes',Y('qgO27MdcAl0'),'Title: with commercials (1 h 42 min). Exact day not stated (placeholder July 5).'),
  ('liberty_closing_abc_1986','Liberty Weekend: Sports Salute to the Statue & Closing Ceremonies','ABC','1986-07-06',1986,1,'yes',A('1986-july-6th-sports-tribute-100th-anniversary-statue-liberty-commercials'),'Original broadcast with commercials (3 h 59 min).'),
  ('macys_fireworks_wpix_1998',"Macy's 4th of July Fireworks Spectacular",'WPIX 11 New York (WB)','1998-07-04',1998,2,'unverified',Y('NWBP1t8I5Ho'),'From an estate-sale tape (42 min); not CBS/ABC/NBC.'),
 ],
 mn=[],
 net=[
  ('wgn_july4_1981','WGN "Happy 4th of July" bumper (1981)','WGN-TV 9 Chicago (independent)','1981-07-04',Y('jG_123aOyrc')),
  ('july4_bumps_1985_87','1980s Fourth of July bumps (WNYW, WPHL, WPVI)','Various','1986-07-04',Y('Jy-SupJ3IYM')),
  ('wfaa_july4_1986','WFAA "Happy 4th of July" card during Liberty Weekend (1986)','ABC / WFAA-TV 8 Dallas','1986-07-04',Y('MSbcWCiZJCw')),
  ('wpta_july4_1986_p1','WPTA/ABC breaks during the Statue of Liberty Centennial (1986) part 1','ABC / WPTA 21 Fort Wayne','1986-07-04',A('wpta-21-abc-commercial-breaks-independence-day-1986-part-1')),
  ('wpta_july4_1986_p2','WPTA/ABC breaks during the Statue of Liberty Centennial (1986) part 2','ABC / WPTA 21 Fort Wayne','1986-07-04',A('wpta-21-abc-commercial-breaks-independence-day-1986-part-2')),
  ('wsjv_july4_1986','WSJV/ABC local breaks, Independence Day 1986','ABC / WSJV 28 South Bend','1986-07-04',A('wsjv-28-abc-local-commercial-breaks-independence-day-1986')),
  ('wndu_july4_1986','WNDU/NBC commercial breaks, Independence Day 1986','NBC / WNDU-TV 16 South Bend','1986-07-04',A('wndu-16-nbc-commercial-breaks-independence-day-1986')),
  ('wabc_liberty_1986','WABC commercials, July 3-5, 1986 (Liberty Weekend)','ABC / WABC-TV 7 New York','1986-07-04',Y('ZBBIBWdzaoA')),
  ('kndo_july4_1999_p1','KNDO/NBC commercials, 4th of July 1999 (part 1)','NBC / KNDO 23 Yakima','1999-07-04',Y('56oK_S6XBqc')),
  ('kndo_july4_1999_p2','KNDO/NBC commercials, 4th of July 1999 (part 2)','NBC / KNDO 23 Yakima','1999-07-04',A('capture-a-2326')),
  ('kndo_july4_1999_p3','KNDO/NBC commercials, 4th of July 1999 (part 3)','NBC / KNDO 23 Yakima','1999-07-04',Y('MFWnwT5lVAo')),
  ('kima_july4_2002','KIMA/CBS commercials, 4th of July 2002 (partial)','CBS / KIMA-TV 29 Yakima','2002-07-04',Y('WKq-2aXS4CE')),
 ]))
