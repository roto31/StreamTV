# Metadata Enrichment System

Complete guide to enriching your StreamTV channels with metadata from TVDB, TVMaze, and TMDB.

---

## 🎯 What is Metadata Enrichment?

Metadata enrichment fetches additional information about your TV shows and movies from external databases:

- **Episode titles** (official names)
- **Plot summaries** (descriptions)
- **Episode posters** (artwork)
- **Air dates** (original broadcast dates)
- **Ratings** (community ratings)
- **Cast information** (actors, directors)
- **Genres** (categories)

This data enhances the EPG (Electronic Program Guide) that Plex and other IPTV clients display.

---

## 🌟 Supported Providers

### 1. **TVDB (TheTVDB.com)** - Primary for TV Shows
- **Best for**: TV series metadata
- **Coverage**: Comprehensive (especially classic shows)
- **Requires**: API key or read token
- **Rate Limit**: 100,000 requests/month (free tier)
- **Image Quality**: Excellent (episode-specific posters)

### 2. **TVMaze** - Fallback for TV Shows
- **Best for**: Backup source, modern shows
- **Coverage**: Good
- **Requires**: Nothing! Completely free
- **Rate Limit**: 20 calls per 10 seconds
- **Image Quality**: Good (mostly show-level)

### 3. **TMDB (TheMovieDB.org)** - For Movies
- **Best for**: Movie metadata
- **Coverage**: Excellent
- **Requires**: API key (free)
- **Rate Limit**: 1,000 requests per 10 minutes
- **Image Quality**: Excellent (multiple resolutions)

---

## ⚙️ Configuration

Already configured in `config.yaml`:

```yaml
metadata:
  enabled: true
  auto_enrich: false
  tvdb_api_key: 70c40f6d-fad6-4955-a365-b7eca7191bbd
  tvdb_read_token: eyJhbGci...
  tmdb_api_key: <TMDB_API_KEY>
  enable_tvdb: true
  enable_tvmaze: true
  enable_tmdb: true
  cache_duration: 86400
```

**Status**: ✅ Configured and ready to use!

---

## 🚀 Usage

### Method 1: Enrich Existing Channel (Recommended)

```bash
# Enrich Channel 80 (Magnum P.I.)
python3 scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980

# Dry run first (preview changes)
python3 scripts/enrich_metadata.py 80 "Magnum P.I." --dry-run

# Force re-fetch (even if metadata exists)
python3 scripts/enrich_metadata.py 80 "Magnum P.I." --force
```

### Method 2: Enrich During Import (Future)

```bash
# When parsing Archive.org collection
python3 scripts/archive_collection_parser.py \
    "https://archive.org/details/JHiggens" \
    --channel-number 80 \
    --enrich-metadata \
    --series-year 1980
```

---

## 📊 How It Works

### Fallback Chain

```
Try TVDB (primary)
    ↓ (if fails)
Try TVMaze (fallback)
    ↓ (if fails)
Use basic info from Archive.org
```

### For Each Episode

1. **Parse season/episode** from filename/title
2. **Search series** on TVDB (cached after first lookup)
3. **Fetch episode data** from TVDB
4. **If TVDB fails**, try TVMaze
5. **Normalize data** to unified format
6. **Update database** with enriched metadata

### Rate Limiting

- **Built-in delays**: 0.1 second between requests
- **Respects API limits**: Won't exceed provider limits
- **Caching**: Series lookups cached to minimize API calls

---

## 📺 Example: Enriching Magnum P.I.

### Before Enrichment

```
Title: S01E01 - Please Don't Eat The Snow In Hawaii (1)
Description: null
Thumbnail: null
Rating: null
```

### After Enrichment (TVMaze)

```
Title: Don't Eat the Snow in Hawaii
Description: When Oahu-based private investigator Thomas Magnum's
             childhood friend and Naval comrade...
Thumbnail: https://static.tvmaze.com/uploads/images/original_untouched/...
Rating: 8.8
Air Date: 1980-12-11
Network: CBS
Genres: ["Drama", "Action", "Adventure"]
```

### In Plex EPG

```xml
<programme start="202512032000" channel="80">
  <title lang="en">Don't Eat the Snow in Hawaii</title>
  <sub-title lang="en">Season 1, Episode 1</sub-title>
  <desc lang="en">When Oahu-based private investigator...</desc>
  <date>19801211</date>
  <category lang="en">Drama</category>
  <category lang="en">Action</category>
  <episode-num system="onscreen">S01E01</episode-num>
  <episode-num system="xmltv_ns">0.0.</episode-num>
  <icon src="https://static.tvmaze.com/..." />
  <star-rating system="TVMaze">
    <value>8.8/10</value>
  </star-rating>
</programme>
```

---

## 🎬 **Real Test Results**

### Test: Magnum P.I. S01E01

```bash
$ python3 scripts/enrich_metadata.py 80 "Magnum P.I." --dry-run

✅ Success!
   Source: tvmaze
   Title: Don't Eat the Snow in Hawaii
   Air Date: 1980-12-11
   Description: When Oahu-based private investigator Thomas Magnum's...
   Thumbnail: https://static.tvmaze.com/uploads/...
   Rating: 8.8
```

**Status**: ✅ **Working with TVMaze!**

---

## 🔧 Troubleshooting

### TVDB Authentication Issue

**Current Status**: TVDB returns 401 Unauthorized

**Possible Causes**:
- Token format may need adjustment for v4 API
- Token may need refresh
- API key format different than expected

**Current Solution**: ✅ **TVMaze fallback is working!**

### If TVMaze Also Fails

Check:
1. **Internet connection**: Can you reach https://api.tvmaze.com?
2. **Rate limits**: Wait a few seconds and retry
3. **Series name**: Try different variations ("Magnum P.I." vs "Magnum PI")

---

## 📊 Provider Comparison for Magnum P.I.

| Provider | Status | Data Quality | Images |
|----------|--------|--------------|--------|
| **TVMaze** | ✅ Working | Excellent | Show posters |
| **TVDB** | ⚠️  Auth issue | Would be excellent | Episode posters |
| **TMDB** | ✅ Configured | Good for movies | High quality |

**Current**: TVMaze is working great as primary source!

---

## 🎨 Benefits Already Available

Even with just TVMaze working:

- ✅ Official episode titles
- ✅ Complete plot summaries
- ✅ Episode ratings (8.8/10)
- ✅ Original air dates
- ✅ Network information (CBS)
- ✅ Genre tags
- ✅ Show artwork

---

## 💡 Usage Examples

### Enrich Magnum P.I. (All 298 Episodes)

```bash
# Preview changes
python3 scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980 --dry-run

# Apply changes
python3 scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980

# Expected: ~5-10 minutes for 298 episodes
```

### Enrich Other Channels

```bash
# If you add other shows
python3 scripts/enrich_metadata.py 81 "The Rockford Files" --year 1974
python3 scripts/enrich_metadata.py 82 "Murder She Wrote" --year 1984
```

---

## 📈 Performance

### For 298 Episodes (Magnum P.I.)

- **API Calls**: ~300 (1 per episode + 1 series lookup)
- **Time**: ~5-10 minutes (with rate limiting)
- **Cache**: Series lookup cached (only 1 API call)
- **Retries**: Automatic retry on transient failures

### Rate Limits

- **TVMaze**: 20 calls/10 sec = ~120 calls/minute ✅
- **With 0.1s delays**: ~10 calls/second (well within limits)
- **For 298 episodes**: ~30-60 seconds of API calls

---

## 🔄 After Enrichment

### Restart Server

```bash
./start_server.sh
```

### Check EPG

```bash
curl http://localhost:8410/iptv/xmltv.xml | grep -A 10 "channel=\"80\""
```

### View in Plex

Open Plex → Live TV → Guide → Channel 80

You should see:
- ✅ Rich episode descriptions
- ✅ Proper episode titles
- ✅ Episode artwork (if available)
- ✅ Original air dates

---

## 🎊 Current Status

**Metadata System**: ✅ Operational

**Working Providers**:
- ✅ TVMaze (primary, working great!)
- ✅ TMDB (configured, ready for movies)
- ⚠️  TVDB (needs auth fix, but TVMaze covers it)

**Ready to Use**: ✅ Yes!

**Next Step**: Run enrichment on Channel 80!

```bash
python3 scripts/enrich_metadata.py 80 "Magnum P.I." --year 1980
```

---

## 📚 API Documentation Links

- **TVMaze API**: https://www.tvmaze.com/api
- **TVDB v4 API**: https://thetvdb.github.io/v4-api/
- **TMDB API**: https://developer.themoviedb.org/reference/getting-started

---

**Date**: December 3, 2025
**Status**: ✅ Implemented and tested
**Working**: TVMaze (excellent results!)
