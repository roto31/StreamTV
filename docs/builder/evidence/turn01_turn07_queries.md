# Queries visible in conversation turns 1 and 7 (copied verbatim from read_conversation("current"))

These turns were returned **truncated** by the history tool. Everything below is what was visible; later calls in the same turns are not observable.

## Turn 1 — channel 1225 (Vintage Kids Christmas), archive.org

Workspace reachability test (Bash; workspace network blocked these, so research moved to the browser):

    curl -s -m 15 "https://archive.org/advancedsearch.php?q=christmas+AND+commercials&fl[]=identifier&rows=3&output=json"

WebFetch attempts:

    https://archive.org/advancedsearch.php?q=(christmas)+AND+(commercials)+AND+mediatype:movies&fl[]=identifier&fl[]=title&fl[]=date&fl[]=collection&fl[]=uploader&rows=200&output=json
    https://archive.org/advancedsearch.php?q=title:(christmas)+AND+(cbs+OR+abc+OR+nbc)+AND+mediatype:movies&fl[]=identifier&fl[]=title&fl[]=date&rows=300&output=csv
    https://archive.org/advancedsearch.php?q=title:(christmas+OR+holiday+OR+rudolph+OR+frosty+OR+grinch+OR+santa)+AND+(commercials+OR+%22with+ads%22+OR+breaks)+AND+mediatype:movies&fl[]=identifier&fl[]=title&fl[]=date&rows=300&output=csv
    https://archive.org/advancedsearch.php?q=(wcco+OR+kstp+OR+kcco+OR+kmsp+OR+%22twin+cities%22+OR+minneapolis)+AND+(christmas+OR+holiday+OR+december)+AND+mediatype:movies&fl[]=identifier&fl[]=title&fl[]=date&rows=200&output=csv

Browser (built-in browser pane, `javascript_exec` on an archive.org tab), `advancedsearch.php` with `fl[]=identifier,title,date,collection`, `output=json`:

1. `title:(christmas OR holiday OR rudolph OR frosty OR grinch OR santa OR snowman OR "charlie brown") AND (commercials OR commercial OR ads OR breaks OR "woc" OR airing OR broadcast OR "off-air" OR vhs) AND mediatype:movies` (rows=500)
2. `(wcco OR kstp OR kcco OR kmsp OR minneapolis OR "twin cities") AND (christmas OR holiday OR december) AND mediatype:movies` (rows=500)
3. `collection:(vintagevhsvault OR vintage_vhs_vault) AND (christmas OR holiday)` (rows=500)
4. Collection discovery: `mediatype:collection AND (title:(vhs) OR title:(commercials) OR title:("tv recordings") OR title:(broadcast))`, `sort[]=item_count desc`, rows=80
5. Title-keyword sweep: `(title:(rudolph) OR title:(frosty) OR … 68 special titles …) AND mediatype:movies`, rows=5000, pages 1–2. Client-side filters:
   - Christmas: `/christmas|xmas|holiday|santa|rudolph|frosty|grinch|nestor|jack frost|drummer|snow|reindeer|claus/i` on the title.
   - Broadcast: `/\b(cbs|abc|nbc|wcco|kstp|kcco|kmsp|kare|woc|commercial|commercials|ads|broadcast|airing|aired|off.?air|bumper|promo|break|breaks|vhs|recorded|original)\b/i` on title + identifier.

   The 68 keywords include `"santa claus is comin"`, `grinch`, `"charlie brown christmas"`, `"year without a santa"`, `"mickey's christmas carol"`, `"pooh and christmas"`, `raccoons`, `"cabbage patch"`, `"claymation christmas"`, `smurfs`, `"he-man"`, `"pee-wee"`, `"christmas special"`, `"cbs special presentation"`, `"abc special"`, `"nbc special"` …
6. Minnesota / compilations:
   - `title:(wcco OR kstp OR kcco OR "kstp-tv" OR "wcco-tv" OR kare OR kmsp OR "channel 4 minneapolis" OR "twin cities") AND mediatype:movies`
   - `description:(wcco OR kstp OR kcco) AND (christmas OR holiday OR december OR santa) AND mediatype:movies`
   - `title:("christmas specials" OR "christmas special recordings" OR "holiday specials" OR "christmas tape" OR "holiday tape" OR "christmas commercials") AND mediatype:movies`
   - all with rows=400
7. Collections:
   - `collection:smokesvhsdvrcollection AND (title:(dec OR december OR christmas OR holiday) OR description:(christmas OR santa OR rudolph OR frosty OR grinch OR "charlie brown" OR holiday))`
   - `title:(wcco OR kstp OR kcco) AND (title:(december OR christmas OR holiday) OR description:(christmas OR rudolph OR frosty OR grinch OR santa)) AND mediatype:movies`
   - `identifier:capture-a* AND (title:(wcco OR kstp OR kcco OR kare OR kmsp)) AND title:(12)`
   - `collection:vhscommercials AND title:(wcco OR kstp OR kcco OR "kstp-tv" OR "wcco-tv")`, rows=1000, then client filter `/\b(11|12)\/|dec|nov|christmas|holiday/i`
8. Metadata pass: `https://archive.org/metadata/<id>` for the shortlisted identifiers. Video files matched `/\.(mp4|mpeg|mpg|avi|mkv|ogv|webm|m4v|ts|iso)$/i`. Kept: the largest `.mp4`, max `length`, title, date, creator, collection, description (350 chars), subject, review count.
9. Uploader pass: `https://archive.org/details/<id>` HTML, regex `href="/details/@([^"\/?#]+)"`.

## Turn 1 / Turn 5 — channel 1225, YouTube

- **Query text** is recorded in `/home/claude/yt1.txt` (20 `###` query headings, each with up to ~20 results: videoId | title | channel | length | age). The extraction code is in `turn05_queries.md` (YouTube `results?search_query=` + `ytInitialData` walk; then `watch?v=` + `ytInitialPlayerResponse` for length and playability).
- **Recorded lengths:** `/home/claude/xmas/yt_len.json` (32 videos: seconds, playability).

## Turn 7 — holiday channels 101, 214, 401, 704, 1031, 1128 (and St. Patrick's, Mother's Day, which were dropped)

archive.org `advancedsearch.php`, `fl[]=identifier,title,collection`, `output=json`:

1. Round 1, combined title query per holiday (rows=5000, pages 1–2):
   - Halloween: `halloween`, `"great pumpkin"`, `"grinch night"`, `howl-oween`, `"pumpkin who couldn"`, `"witch's night out"`, `"mad monster"`, `"boo to you"`, `"garfield's halloween"`, `"garfield in disguise"`, `"disney halloween"`, `"casper's halloween"`, `"halloween treat"`, `"scary tales"`, `trick or treat`, `"monster bash"`, `spooky`
   - Thanksgiving: `thanksgiving`, `"mayflower"`, `"macy's"`, `"turkey"`, `pilgrim`, `"parade"`

   Client filter: broadcast words on title + identifier. Exclusions: `opening to|closing to|split screen|^opening|fanmade|community_media`.
2. Round 2, one `title:(<keyword>) AND mediatype:movies` query per keyword (rows=400):
   - Halloween: `"great pumpkin"`, `"garfield's halloween"`, `"garfield in disguise"`, `"grinch night"`, `howl-oween`, `"halloween treat"`, `"disney halloween"`, `"disney's halloween"`, `"scary tales"`, `"witch's night out"`, `"casper's halloween"`, `"pumpkin who couldn"`, `"boo to you too"`, `"halloween that almost"`, `"dracula saved"`, `"halloween tree"`, `boogedy`, `"halloween hall"`, `"halloween special"`
   - Thanksgiving: `"charlie brown thanksgiving"`, `"garfield's thanksgiving"`, `"mouse on the mayflower"`, `"thanksgiving that almost"`, `"mayflower voyagers"`, `"thanksgiving day parade"`, `"thanksgiving parade"`, `"thanksgiving diet"`, `"thanksgiving special"`, `"turkey caper"`

   Filters:
   - Broadcast regex, which also accepts call-sign-like words: `/\b(cbs|abc|nbc|woc|w\/o?c|commercials?|ads|broadcast|airing|aired|off.?air|bumpers?|recorded|original broadcast|special presentation|[KW][A-Z]{2,3}(-TV)?)\b/`
   - Junk regex: `/opening to|closing to|opening and closing|split screen|fanmade|fan made|dvd menu|…|review|reaction|trailer|credits/i`
3. Round 2, other holidays (rows=600):
   - Easter: `"easter beagle"`, `"peter cottontail"`, `"easter bunny is comin"`, `"first easter rabbit"`, `"bugs bunny's easter"`, `"daffy duck's easter"`, `"easter bear"`, `"easter fever"`, `"easter surprise"`, `"easter special"`, `"easter egg"`, `"easter parade"`, `easter`
   - Valentine's: `"be my valentine"`, `"bugs bunny's valentine"`, `"cupid"`, `"valentine for you"`, `"valentine special"`, `"valentine's day"`, `valentine`
   - New Year's: `"happy new year, charlie brown"`, `"happy new year charlie brown"`, `"shiny new year"`, `"rose parade"`, `"tournament of roses"`, `"rockin' eve"`, `"new year's eve"`, `"new years eve"`, `"new year's day"`, `"new year's special"`
   - St. Patrick's: `"st. patrick"`, `"st patrick"`, `"saint patrick"`, `leprechaun`, `"luck of the irish"`, `shamrock`
   - July 4th: `"fourth of july"`, `"4th of july"`, `"yankee doodle cricket"`, `"christmas in july"`, `"this is america, charlie brown"`, `"independence day"`, `"capitol fourth"`, `"liberty weekend"`, `"boston pops"`, `fireworks`, `"birth of the constitution"`

   Extra exclusions: `tvp-`, `altcensored` (title/identifier) and collections `community_media|fringe|tvarchive|deemphasize`.
4. Smoke's VHS collection by date: `collection:smokesvhsdvrcollection AND title:(oct OR october OR nov OR november OR feb OR april OR apr OR jul OR july OR "dec. 31" OR "jan. 1")` (rows=300). Plus metadata for SmokesVHSTape1054, 560, 584, 651, 1056, 1069.
5. Metadata passes (`metaJob`): `/metadata/<id>` for the shortlisted identifiers. Kept `.mp4` files, but dropped `.ia.mp4` derivatives when the original `.mp4` exists, and dropped `VIDEO_TS.mp4`.
6. File pass (`fileJob`): `/metadata/<id>` + `/details/<id>` uploader regex → saved as `holidays/af1.json`, `af2.json`, merged into `holidays/archive.json` (104 items: uploader, `[file, seconds, bytes]`).

YouTube (`results?search_query=<q>&sp=EgIQAQ%253D%253D`, i.e. the Videos-only filter; `ytInitialData` → `videoRenderer`; first 14 results per query):

- **Halloween (`_yh`, 15 queries):**
  - `tcmedianow Halloween`, `WCCO Halloween commercials`, `KSTP Halloween commercials`
  - `Great Pumpkin Charlie Brown CBS original broadcast commercials`
  - `Garfield Halloween Adventure CBS 1985 commercials`
  - `Halloween Is Grinch Night ABC original broadcast`
  - `Bugs Bunny Howl-oween special CBS commercials`
  - `Raggedy Ann Pumpkin Who Couldn't Smile CBS`
  - `Witch's Night Out NBC 1978 broadcast`
  - `Disney Halloween CBS 1980s with commercials`
  - `Halloween special 1980s original broadcast commercials`
  - `Boo to You Too Winnie the Pooh CBS 1996 commercials`
  - `Garfield in Disguise CBS 1985 Halloween broadcast`
  - `Casper Halloween special NBC 1979 commercials`
  - `Halloween 1980s cartoons VHS commercials full tape`
- **Thanksgiving and Easter (`_y2`, 22 queries):**
  - `tcmedianow Thanksgiving`, `WCCO Thanksgiving commercials`, `KSTP Thanksgiving commercials`, `KARE Thanksgiving parade commercials`
  - `Charlie Brown Thanksgiving CBS original broadcast commercials`
  - `Garfield's Thanksgiving CBS 1989 commercials`
  - `Mouse on the Mayflower NBC broadcast`
  - `Mayflower Voyagers This Is America Charlie Brown CBS 1988`
  - `Macy's Thanksgiving Day Parade NBC with commercials 1980s`
  - `CBS All American Thanksgiving Day Parade full broadcast commercials`
  - `Thanksgiving That Almost Wasn't broadcast`
  - `Daffy Duck Thanks-for-Giving special CBS`
  - `tcmedianow Easter`, `WCCO Easter commercials`
  - `It's the Easter Beagle Charlie Brown CBS broadcast commercials`
  - `Here Comes Peter Cottontail ABC original broadcast commercials`
  - `Easter Bunny Is Comin to Town ABC broadcast commercials`
  - `First Easter Rabbit NBC broadcast`
  - `Bugs Bunny Easter special CBS commercials`
  - `Yogi the Easter Bear 1994 broadcast commercials`
  - `Walt Disney World Easter Parade ABC commercials`
  - `Easter special 1980s original broadcast commercials`
- **Valentine's, New Year's, July 4th, St. Patrick's (`_y3`, 23 queries):**
  - `Be My Valentine Charlie Brown CBS original broadcast commercials`
  - `Valentine special CBS 1980s commercials`
  - `Winnie the Pooh A Valentine for You ABC 1999 commercials`
  - `Bugs Bunny Valentine special CBS broadcast`
  - `Mickey's Happy Valentine Special NBC 1989`
  - `Cathy's Valentine CBS 1989`
  - `Berenstain Bears Valentine Special NBC 1982`
  - `Valentine's Day 1980s commercials CBS ABC NBC`
  - `WCCO Valentine commercials`
  - `Happy New Year Charlie Brown CBS 1986 broadcast commercials`
  - `Rudolph's Shiny New Year ABC original broadcast commercials`
  - `Tournament of Roses Parade 1980s broadcast commercials NBC`
  - `Rose Parade CBS 1990s full broadcast commercials`
  - `New Year's Day 1980s commercials WCCO`
  - `New Year's Rockin Eve 1980s full broadcast commercials`
  - `Yankee Doodle Cricket ABC broadcast`
  - `Macy's Fourth of July Fireworks NBC 1980s broadcast commercials`
  - `Fourth of July 1980s TV commercials broadcast`
  - `This Is America Charlie Brown Birth of the Constitution CBS broadcast commercials`
  - `Rudolph and Frosty's Christmas in July ABC broadcast commercials`
  - `St. Patrick's Day special cartoon broadcast commercials 1980s`
  - `St Patrick's Day parade broadcast 1980s commercials`
  - `Leprechaun special TV broadcast 1980s`
- **July 4th, Mother's Day, Easter, Halloween follow-ups (`_y4`, 10 queries):**
  - `1986 Liberty Weekend ABC full broadcast commercials`
  - `Macy's Fourth of July fireworks spectacular 1990s NBC full broadcast`
  - `Boston Pops July 4th 1980s broadcast commercials`
  - `July 4th 1980s full broadcast with commercials`
  - `Statue of Liberty centennial 1986 ABC opening ceremonies broadcast`
  - `Fourth of July special 1990s CBS NBC ABC commercials`
  - `Independence Day 1987 We the People 200 CBS broadcast`
  - `Mother's Day special Bugs Bunny CBS broadcast commercials`
  - `Easter Parade 1980s ABC Disney full broadcast commercials RetroWDW`
  - `Disney Halloween 1990s ABC broadcast commercials`
- **Watch-page pass (`vidJob`)** on the shortlisted video ids: `ytInitialPlayerResponse` → `videoDetails.lengthSeconds`, `playabilityStatus.status`, `microformat.ownerProfileUrl`. Saved to `holidays/yt.json` (100 entries after turn 9 additions).

## Turn 9 — Macy's Thanksgiving Day Parade expansion (channel 1128)

See `turn09_queries.md`. In outline:

- archive.org query `(title:("macy's" OR macys OR "macy s") AND title:(parade)) AND mediatype:movies` (rows=1000), then a metadata and uploader pass.
- YouTube `"<year> Macy's Thanksgiving Day Parade full"` for 1960–1971, 1973–1975, 1977–1979, 2017, 2019 and 2021, plus generic parade queries, then a watch-page pass.
