"""Per-channel SOURCES.md text: collections, extra finds and gaps."""

TERMS = """- **Off-air capture** — a recording someone made at home by taping the TV signal as it aired (VHS or Betamax), later digitized. It shows TV exactly as it was broadcast.
- **Commercials / station breaks** — the ad breaks between program segments. Local stations inserted their own ads, so the same special looks different city to city.
- **Bumpers** — the short "We'll be right back" / "Now back to…" cards and voiceovers on either side of a break.
- **Station identification (ID)** — the local channel's logo or announcement (for example "WCCO 4"). A recording "carries a local identity" when you see the local station rather than only the network.
- **O&O / affiliate** — an O&O is a station the network owns (WMAQ Chicago for NBC); an affiliate is an independent station that carries the network (WCCO for CBS, KSTP for ABC, KARE for NBC).
- **WOC** — "with original commercials". Several uploaders put it in titles. Where WOC is the only evidence, this guide says so.
- **Uploader** — the person or account that posted the item. Following an uploader's page shows everything else they posted.
- **Playlist / collection** — a group of related videos (YouTube) or items (archive.org) you can follow as one set.
- **Tier 1 / Tier 2** — Tier 1 is a strong match: a {{HOLIDAY}} program on CBS, ABC or NBC from the 1980s to early 2000s, with commercials confirmed by the description or title. Tier 2 is a partial match: one of those points is missing or unconfirmed (other network, outside the years, commercials not confirmed, or not made for kids)."""

C_IMTA = ('Indiana-Michigan TV Archives (@indianamichigantvarchives)', 'archive.org',
          'Complete commercial breaks from South Bend / Fort Wayne stations (WNDU, WSBT, WSJV, WPTA, WKJG), titled by holiday and year.',
          'https://archive.org/details/@indianamichigantvarchives')
C_AVTB = ('The AVTB Archives (capture-a series, @vhsgoodieswa3)', 'archive.org + YouTube',
          'Thousands of short "capture-a-NNNN" ad reels from West Coast stations (KIMA, KNDO, KCRA, KRON, KING, KOMO, KABC), each dated.',
          'https://archive.org/details/@vhsgoodieswa3')
C_SMOKE = ("Smoke's VHS/DVR Collection", 'archive.org', 'Minneapolis–St. Paul off-air tapes (KARE, KSTP, WCCO, KMSP) split into dated commercial reels.',
           'https://archive.org/details/smokesvhsdvrcollection')
C_TVMA = ('tvandmoviearchive', 'YouTube + archive.org', 'WCCO, KSTP and KARE commercial reels by date.', 'https://www.youtube.com/@tvandmoviearchive')
C_TCMN = ('TCMediaNow (Twin Cities Media Now)', 'YouTube', 'Twin Cities non-profit digitizing local TV. Its Halloween and Thanksgiving items are news coverage (see gaps), not kids programs.',
          'https://www.youtube.com/@tcmedianow')
C_MCCT = ('The Museum of Classic Chicago Television', 'YouTube (mirrored on archive.org)', 'Complete Chicago broadcasts with every break itemized (WLS, WBBM, WMAQ).',
          'https://www.youtube.com/@FuzzyMemoriesTV')

EXTRAS = {
'1031': dict(holiday="kids' Halloween",
  intro='Channel 1031 plays Halloween specials in air-date order with a real break reel between each one.',
  collections=[
    C_MCCT,
    ("Walt's Vault (@walt_s_vault_)", 'archive.org', 'Disney anthology Halloween broadcasts from CBS (A Disney Halloween 1981, Disney\'s Halloween Treat 1982/1983).', 'https://archive.org/details/@walt_s_vault_'),
    ('The Vista Group (@the_vista_group)', 'archive.org', 'Unedited Pittsburgh off-air tapes, including KDKA Halloween night 1985.', 'https://archive.org/details/@the_vista_group'),
    ('Kev The Ripper (@kevripzzz)', 'YouTube', 'Rare 1980 CBS Raggedy Ann Halloween airing with ads.', 'https://www.youtube.com/@kevripzzz'),
    C_AVTB, C_SMOKE, C_TVMA, C_TCMN,
  ],
  also=[
    '[A Disney Halloween 1981 (YouTube, 89 min)](https://www.youtube.com/watch?v=3LsK-RBN9IA) — duplicate of the archive.org CBS copy; commercials not stated.',
    "Scenes-only uploads of Halloween Is Grinch Night and Garfield's Halloween Adventure were skipped (not full broadcasts).",
  ],
  gaps=[
    'KCCO 7 Alexandria: nothing found for Halloween.',
    'WCCO/KSTP full programs: no complete Halloween special recorded off a Minnesota station turned up, only the three break reels.',
    'TCMediaNow Halloween items found are news (the 1991 Halloween Blizzard), not kids programming, so they were not loaded.',
    "It's the Great Pumpkin, Charlie Brown: no stand-alone 1980s–90s CBS airing with commercials was found; it appears inside the 1985 CBS double bill, the 2002 ABC/WHTM tape and several break reels.",
    'Dates marked as placeholders in notes (1985 CBS Garfield + Great Pumpkin) are estimates.',
    'YouTube videos can disappear at any time. Run the installer\'s URL check before each season.',
  ]),
'1128': dict(holiday="Thanksgiving (kids' specials or the parades)",
  intro=("Channel 1128 holds the Thanksgiving specials plus one Macy's Thanksgiving Day Parade per year for every year a recording was found "
         "(1939, 1959, 1965–69 footage, 1972 and every year from 1976 to 2025), plus eight CBS All-American Thanksgiving Day Parades. "
         "Full recordings were preferred; partials were used only where nothing fuller exists for that year. Everything runs in air-date order with a break reel between programs."),
  program_sections=[("Macy's Thanksgiving Day Parade", lambda p: p['sid'].startswith('macys_parade_')),
                    ('CBS All-American Thanksgiving Day Parade', lambda p: p['sid'].startswith('cbs_all_american')),
                    ('Specials and tapes', lambda p: not (p['sid'].startswith('macys_parade_') or p['sid'].startswith('cbs_all_american')))],
  collections=[
    ("applelol — Macy's parade series", 'archive.org', 'Uploaded most of the full 1989–2016 Macy\'s parades (the "videoplaybackN" and "untitledN" items).', 'https://archive.org/details/@applelol'),
    ('Tape Hole Annex', 'YouTube', 'Wisconsin off-air tapes with commercials: Macy\'s 1990 (WLUK) and CBS All-American Parades 1984–1986 (WSAW, WBAY).', 'https://www.youtube.com/@tapeholeannex'),
    ('defcon1919 (@discontinued2090)', 'YouTube', "Long NBC Macy's telecasts from 1983 (two parts), 1984 and 1985.", 'https://www.youtube.com/@discontinued2090'),
    ('Obsolete Video', 'YouTube', "Restored 1970s Macy's footage (1976 complete, 1979 partial) and a 1972 KNBC/KABC commercial reel.", 'https://www.youtube.com/@obsoletevideo6048'),
    C_IMTA, C_AVTB, C_SMOKE, C_TVMA, C_TCMN, C_MCCT,
  ],
  also=[
    "[A Thanksgiving Tale (1983) 'classic special' upload](https://archive.org/details/classic-thanksgiving-special-a-thanksgiving-tale-1983) — the commercials were added later from other tapes, so it is not a real broadcast.",
    "Duplicate Macy's copies for the same year were skipped (only the most complete per year was kept).",
    '[CBS All-American 1986 alternate copy](https://www.youtube.com/watch?v=J7DOv73NZtg) — same parade as the WBAY copy that is loaded.',
    '1982 CBS All-American Parade on archive.org exists only as a .webm file, so the YouTube copy is used instead.',
  ],
  gaps=[
    "Macy's years with no recording found: 1940–1958, 1960–1964, 1970, 1971, 1973–1975. 1965–1969 exist only as an 11-minute footage reel (and 1968 as a 19-minute partial).",
    "Partial Macy's years (kept because nothing fuller exists): 1965–69, 1968, 1972, 1977, 1978 (CBS coverage), 1979, 1983 (two parts).",
    "Most 1986–2020 Macy's uploads have the commercials cut out (the runtime is about 2 h 10 min to 2 h 25 min instead of 3 h). Years with commercials confirmed: 1981, 1988, 1989, 1990, 2002, 2004, 2023.",
    "The 2025 file is 5 h 32 min and likely includes pre-show or post-parade coverage. The 1987 file continues into an NFL game.",
    'KCCO 7 Alexandria: nothing found. KARE 11 has one break reel taped during the 1991 Macy\'s Parade; no full KARE parade recording was found.',
    "A Charlie Brown Thanksgiving: no stand-alone 1980s–90s CBS airing with commercials was found; a partial is on the 1984 tape.",
    'TCMediaNow Thanksgiving items found are news (the 1982 Thanksgiving Day fire in Minneapolis), not kids programming, so they were not loaded.',
    'Air dates for parades are the Thanksgiving Day of that year.',
  ]),
'401': dict(holiday="kids' Easter",
  intro="Channel 401 plays Easter specials and ABC's Walt Disney World Happy Easter Parades in air-date order with a real break reel between each one.",
  collections=[
    ('RetroWDW', 'YouTube', "The Lake Buena Vista Historical Society's Disney World archive: ABC Happy Easter Parades 1988–1999.", 'https://www.youtube.com/@RetroWDW'),
    C_IMTA, C_AVTB, C_MCCT,
  ],
  also=[
    "The Peanuts and Rankin/Bass Easter specials (It's the Easter Beagle, Here Comes Peter Cottontail) aired many times in the 1980s, but no 1980s–90s network airing with commercials turned up except the 1978 WTOP tape and the 2004 ABC Family airing.",
  ],
  gaps=[
    'Minnesota: no WCCO, KSTP, KARE or KCCO Easter recording or break reel was found.',
    'Most RetroWDW parade uploads do not say whether the commercials are in.',
    'Easter Sunday dates were filled in from the calendar where the item gave only the year.',
    "St. Patrick's Day and Mother's Day were also searched; too little vintage broadcast material exists to make a channel.",
  ]),
'214': dict(holiday="Valentine's Day",
  intro="Channel 214 is the smallest channel. Only three Valentine's specials with broadcast context turned up, so it loops more often and leans on break reels.",
  collections=[C_SMOKE, C_MCCT,
    ('NewDVRLovers2017', 'YouTube', 'Late-80s CBS break reels, including WCBS during Cathy\'s Valentine.', 'https://www.youtube.com/@NewDVRLovers2017')],
  also=[
    '[Disney Valentine special, 1986/1991 (AI-enhanced)](https://www.youtube.com/watch?v=M_Jmu5bHEqQ) — the picture was altered by AI upscaling, so it was not loaded.',
    "Be My Valentine, Charlie Brown: only the 1979 WBBM opening and break reel was found; there is no full 1980s–90s airing with commercials.",
  ],
  gaps=[
    "Very few full Valentine's broadcasts survive. Expect frequent repeats; add more break reels if you find them.",
    'KSTP and KCCO: nothing found for February.',
    'The WCCO and KARE reels are February reels, not tied to a Valentine\'s special.',
  ]),
'101': dict(holiday="New Year's",
  intro=("Channel 101 is broadened beyond kids' programming because almost no kids' New Year's specials exist. It mixes the Tournament of Roses Parade, "
         "Dick Clark's New Year's Rockin' Eve and Rudolph's Shiny New Year. The Happy New Year, Charlie Brown breaks are in the break rotation because no full airing with commercials was found."),
  collections=[C_IMTA, C_AVTB,
    ('Tape Hole Annex', 'YouTube', 'Wisconsin off-air Rose Parades with commercials: 1985 (WBAY/CBS) and 1988 (WLUK/NBC).', 'https://www.youtube.com/@tapeholeannex'),
    ('peppardb', 'YouTube', 'CBS 1987 Happy New Year, Charlie Brown break sets (four parts).', 'https://www.youtube.com/@peppardb'),
    ('Off-Air Vault (@offairvault)', 'archive.org', 'Long Los Angeles off-air tapes, including KTLA Rose Parade 2000.', 'https://archive.org/details/@offairvault')],
  also=['Rockin\' Eve broadcasts are adult programming; remove the three rockin_eve_ ids if you want the channel kids-only.'],
  gaps=[
    'Minnesota: no WCCO, KSTP, KARE or KCCO New Year\'s recording or break reel was found.',
    'Happy New Year, Charlie Brown (CBS 1986): only break reels were found, not a full airing.',
    'The 1997 CBS Rose Parade item title says January 2, 1997 (the parade was January 1).',
  ]),
'704': dict(holiday='Fourth of July (family)',
  intro=("Channel 704 is broadened to family programming: there are no kids' July 4th specials. It is built around ABC's 1986 Liberty Weekend coverage "
         "(the Statue of Liberty centennial), plus a 1998 Macy's fireworks broadcast and holiday station bumpers."),
  collections=[C_IMTA, C_AVTB, C_MCCT],
  also=['[KNBC Macy\'s fireworks (undated)](https://www.youtube.com/watch?v=u3GCyDsf9rE) — no year, so it was left out.'],
  gaps=[
    'Minnesota: no WCCO, KSTP, KARE or KCCO July 4th recording or break reel was found.',
    "Macy's Fourth of July Fireworks broadcasts from NBC in the 1980s–90s were not found; the 1998 copy is from WPIX.",
    'One Liberty Weekend broadcast day is a placeholder (July 5, 1986), noted in its entry.',
  ]),
}
