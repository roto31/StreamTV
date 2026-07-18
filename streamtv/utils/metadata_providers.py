"""
Metadata providers for TV shows and movies
Integrates with TVDB, TVMaze, and TMDB APIs
"""

import httpx
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class TVDBClient:
    """The TVDB (TheTVDB.com) API v4 client for TV show metadata"""
    
    def __init__(self, api_key: str, read_token: Optional[str] = None):
        self.api_key = api_key
        self.read_token = read_token  # Bearer token for API v4
        self.base_url = "https://api4.thetvdb.com/v4"
        self._auth_token = None
        self._token_expires = None
        
    async def _ensure_authenticated(self) -> str:
        """Ensure we have a valid auth token"""
        if self._auth_token and self._token_expires:
            if datetime.utcnow() < self._token_expires:
                return self._auth_token
        
        # Use read token if provided (TVDB v4 uses bearer tokens)
        if self.read_token:
            self._auth_token = self.read_token
            # Read tokens don't expire
            return self._auth_token
        
        # Otherwise, authenticate with API key (legacy method)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/login",
                    json={"apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                self._auth_token = data.get('data', {}).get('token')
                return self._auth_token
        except Exception as e:
            logger.error(f"TVDB authentication failed: {e}")
            raise
    
    async def search_series(self, name: str) -> Optional[Dict[str, Any]]:
        """Search for a TV series by name"""
        try:
            token = await self._ensure_authenticated()
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # TVDB v4 uses query parameter 'q' not 'query'
                response = await client.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params={"q": name}
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get('data', [])
                if results:
                    # Filter for series type
                    for result in results:
                        if result.get('type') == 'series' or result.get('objectID'):
                            return result
                    # Return first if no type filter matches
                    return results[0]
                return None
        except Exception as e:
            logger.error(f"TVDB search failed for '{name}': {e}")
            return None
    
    async def get_series_details(self, series_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a series"""
        try:
            token = await self._ensure_authenticated()
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/series/{series_id}/extended",
                    headers=headers
                )
                response.raise_for_status()
                return response.json().get('data')
        except Exception as e:
            logger.error(f"TVDB series details failed for ID {series_id}: {e}")
            return None
    
    async def get_episode(
        self, 
        series_id: int, 
        season: int, 
        episode: int
    ) -> Optional[Dict[str, Any]]:
        """Get episode metadata by season and episode number"""
        try:
            token = await self._ensure_authenticated()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get all episodes for the series
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/series/{series_id}/episodes/default",
                    headers=headers,
                    params={"page": 0}
                )
                response.raise_for_status()
                data = response.json()
                
                episodes = data.get('data', {}).get('episodes', [])
                
                # Find matching episode
                for ep in episodes:
                    if ep.get('seasonNumber') == season and ep.get('number') == episode:
                        return ep
                
                # Check additional pages if needed
                pages = data.get('data', {}).get('totalPages', 1)
                for page in range(1, min(pages, 10)):  # Limit to 10 pages
                    response = await client.get(
                        f"{self.base_url}/series/{series_id}/episodes/default",
                        headers=headers,
                        params={"page": page}
                    )
                    response.raise_for_status()
                    data = response.json()
                    episodes = data.get('data', {}).get('episodes', [])
                    
                    for ep in episodes:
                        if ep.get('seasonNumber') == season and ep.get('number') == episode:
                            return ep
                
                logger.warning(f"TVDB episode not found: S{season:02d}E{episode:02d}")
                return None
                
        except Exception as e:
            logger.error(f"TVDB episode fetch failed: {e}")
            return None


class TVMazeClient:
    """TVMaze API client for TV show metadata (free, no API key required)"""
    
    def __init__(self):
        self.base_url = "https://api.tvmaze.com"
    
    async def search_show(self, name: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a TV show by name, optionally filtered by year"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use full search to get multiple results if year specified
                if year:
                    response = await client.get(
                        f"{self.base_url}/search/shows",
                        params={"q": name}
                    )
                    response.raise_for_status()
                    results = response.json()
                    
                    # Filter results by year (premiered date)
                    for result in results:
                        show = result.get('show', {})
                        premiered = show.get('premiered', '')
                        if premiered:
                            show_year = int(premiered[:4])
                            # Match year with tolerance of +/- 1 year
                            if abs(show_year - year) <= 1:
                                logger.info(f"Found {show.get('name')} ({show_year}) matching year {year}")
                                return show
                    
                    # If no year match, return first result with warning
                    if results:
                        show = results[0].get('show', {})
                        logger.warning(f"No exact year match for {year}, using: {show.get('name')} ({show.get('premiered', 'unknown')})")
                        return show
                    return None
                else:
                    # Single search when no year specified
                    response = await client.get(
                        f"{self.base_url}/singlesearch/shows",
                        params={"q": name}
                    )
                    response.raise_for_status()
                    return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"TVMaze: Show not found: '{name}'")
            else:
                logger.error(f"TVMaze search failed for '{name}': {e}")
            return None
        except Exception as e:
            logger.error(f"TVMaze search error: {e}")
            return None
    
    async def get_episode(
        self, 
        show_id: int, 
        season: int, 
        episode: int
    ) -> Optional[Dict[str, Any]]:
        """Get episode metadata by season and episode number"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/shows/{show_id}/episodebynumber",
                    params={"season": season, "number": episode}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"TVMaze: Episode not found: S{season:02d}E{episode:02d}")
            else:
                logger.error(f"TVMaze episode fetch failed: {e}")
            return None
        except Exception as e:
            logger.error(f"TVMaze episode error: {e}")
            return None
    
    async def lookup_by_tvdb_id(self, tvdb_id: int) -> Optional[Dict[str, Any]]:
        """Lookup show by TVDB ID"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/lookup/shows",
                    params={"thetvdb": tvdb_id}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.debug(f"TVMaze lookup by TVDB ID failed: {e}")
            return None


class TMDBClient:
    """The Movie Database (TMDB) API client for movie metadata"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
    
    async def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a movie by title"""
        try:
            params = {
                "api_key": self.api_key,
                "query": title
            }
            if year:
                params["year"] = year
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/search/movie",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                if not results:
                    return None
                return self._pick_best_movie_result(title, year, results)
        except Exception as e:
            logger.error(f"TMDB movie search failed for '{title}': {e}")
            return None

    @staticmethod
    def _normalize_title_tokens(title: str) -> set:
        import re
        t = (title or "").lower()
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        # Roman / ordinal synonyms for sequels
        t = re.sub(r"\bii\b", "2", t)
        t = re.sub(r"\biii\b", "3", t)
        t = re.sub(r"\btwo\b", "2", t)
        t = re.sub(r"\bthree\b", "3", t)
        stop = {"the", "a", "an", "of", "and"}
        return {w for w in t.split() if w and w not in stop}

    def _pick_best_movie_result(
        self,
        query: str,
        year: Optional[int],
        results: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Prefer title/year-compatible hits; reject loose first-result matches."""
        q_tokens = self._normalize_title_tokens(query)
        if not q_tokens:
            return results[0]

        best = None
        best_score = -1.0
        for movie in results[:10]:
            cand = movie.get("title") or movie.get("original_title") or ""
            c_tokens = self._normalize_title_tokens(cand)
            if not c_tokens:
                continue
            overlap = len(q_tokens & c_tokens) / len(q_tokens)
            extra = len(c_tokens - q_tokens)
            # Reject candidates that add significant unique tokens (e.g. LEGO, Name)
            if overlap < 0.8 or extra > 1:
                continue
            score = overlap * 10 - extra
            release = (movie.get("release_date") or "")[:4]
            if year and release.isdigit():
                dy = abs(int(release) - year)
                if dy == 0:
                    score += 5
                elif dy == 1:
                    score += 2
                elif dy > 3:
                    score -= 5
            if score > best_score:
                best_score = score
                best = movie
        if best is None:
            logger.warning(
                "TMDB: no title-compatible match for %r (year=%s); rejecting loose hits",
                query,
                year,
            )
        return best
    
    async def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a movie"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/movie/{movie_id}",
                    params={
                        "api_key": self.api_key,
                        "append_to_response": "credits,keywords,images"
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TMDB movie details failed for ID {movie_id}: {e}")
            return None
    
    async def search_tv_show(self, name: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a TV show by name"""
        try:
            params = {
                "api_key": self.api_key,
                "query": name
            }
            if year:
                params["first_air_date_year"] = year
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/search/tv",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                if results:
                    return results[0]
                return None
        except Exception as e:
            logger.error(f"TMDB TV search failed for '{name}': {e}")
            return None
    
    async def get_tv_episode(
        self, 
        tv_id: int, 
        season: int, 
        episode: int
    ) -> Optional[Dict[str, Any]]:
        """Get TV episode metadata"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/tv/{tv_id}/season/{season}/episode/{episode}",
                    params={"api_key": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TMDB TV episode fetch failed: {e}")
            return None


class MetadataManager:
    """Unified metadata manager with fallback support"""
    
    def __init__(
        self,
        tvdb_client: Optional[TVDBClient] = None,
        tvmaze_client: Optional[TVMazeClient] = None,
        tmdb_client: Optional[TMDBClient] = None
    ):
        self.tvdb = tvdb_client
        self.tvmaze = tvmaze_client
        self.tmdb = tmdb_client
        self._series_cache = {}  # Cache series lookups
    
    async def get_tv_episode_metadata(
        self,
        series_name: str,
        season: int,
        episode: int,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get TV episode metadata with fallback support
        
        Args:
            series_name: Name of the TV series
            season: Season number
            episode: Episode number
            year: Optional year for better matching
            
        Returns:
            Unified metadata dictionary or None
        """
        from streamtv.utils.media_meta import prefer_longest_description

        tvdb_meta = None
        tvmaze_meta = None

        # Try TVDB first (primary source)
        if self.tvdb:
            try:
                tvdb_meta = await self._get_tvdb_episode(
                    series_name, season, episode, year
                )
                if tvdb_meta:
                    logger.info(
                        f"✅ TVDB metadata for {series_name} "
                        f"S{season:02d}E{episode:02d}"
                    )
            except Exception as e:
                logger.warning(f"TVDB failed, trying fallback: {e}")

        # Also consult TVMaze for completeness / longest description
        if self.tvmaze:
            try:
                tvmaze_meta = await self._get_tvmaze_episode(
                    series_name, season, episode, year
                )
                if tvmaze_meta:
                    logger.info(
                        f"✅ TVMaze metadata for {series_name} "
                        f"S{season:02d}E{episode:02d}"
                    )
            except Exception as e:
                logger.warning(f"TVMaze also failed: {e}")

        if tvdb_meta and tvmaze_meta:
            return prefer_longest_description(tvdb_meta, tvmaze_meta)
        if tvdb_meta:
            out = prefer_longest_description(tvdb_meta, None)
            return out
        if tvmaze_meta:
            return prefer_longest_description(tvmaze_meta, None)

        logger.warning(f"❌ No metadata found for {series_name} S{season:02d}E{episode:02d}")
        return None
    
    async def _get_tvdb_episode(
        self,
        series_name: str,
        season: int,
        episode: int,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get episode metadata from TVDB"""
        # Check cache with year to distinguish remakes/reboots
        cache_key = f"tvdb_{series_name}_{year}" if year else f"tvdb_{series_name}"
        if cache_key not in self._series_cache:
            # Search for series
            series = await self.tvdb.search_series(series_name)
            if not series:
                return None
            # TODO: Filter by year when available in TVDB response
            self._series_cache[cache_key] = series
        else:
            series = self._series_cache[cache_key]
        
        series_id = series.get('tvdb_id') or series.get('id')
        if not series_id:
            return None
        
        # Get episode
        episode_data = await self.tvdb.get_episode(series_id, season, episode)
        if not episode_data:
            return None
        
        # Normalize to unified format
        metadata = self._normalize_tvdb_episode(episode_data, series)
        # TVDB search hits often omit genres — fill from TVMaze show record (cached)
        if not metadata.get("genres") and self.tvmaze:
            gkey = f"tvmaze_show_{series_name}_{year}"
            try:
                if gkey not in self._series_cache:
                    self._series_cache[gkey] = await self.tvmaze.search_show(
                        series_name, year=year
                    )
                show = self._series_cache.get(gkey) or {}
                if show.get("genres"):
                    metadata["genres"] = list(show.get("genres") or [])
            except Exception as exc:
                logger.debug("TVMaze genre fill after TVDB failed: %s", exc)
        return metadata
    
    async def _get_tvmaze_episode(
        self,
        series_name: str,
        season: int,
        episode: int,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get episode metadata from TVMaze"""
        # Check cache with year to distinguish remakes/reboots
        cache_key = f"tvmaze_{series_name}_{year}" if year else f"tvmaze_{series_name}"
        if cache_key not in self._series_cache:
            # Search for show with year filtering
            show = await self.tvmaze.search_show(series_name, year=year)
            
            if not show:
                return None
            self._series_cache[cache_key] = show
        else:
            show = self._series_cache[cache_key]
        
        show_id = show.get('id')
        if not show_id:
            return None
        
        # Get episode
        episode_data = await self.tvmaze.get_episode(show_id, season, episode)
        if not episode_data:
            return None
        
        # Normalize to unified format
        return self._normalize_tvmaze_episode(episode_data, show)
    
    def _normalize_tvdb_episode(
        self,
        episode: Dict[str, Any],
        series: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize TVDB episode data to unified format"""
        # Extract image URL
        image_url = None
        if episode.get('image'):
            image_url = episode['image']
        elif episode.get('filename'):
            image_url = f"https://artworks.thetvdb.com/banners/{episode['filename']}"
        
        return {
            'source': 'tvdb',
            'title': episode.get('name', ''),
            'description': episode.get('overview', ''),
            'season': episode.get('seasonNumber'),
            'episode': episode.get('number'),
            'air_date': episode.get('aired', ''),
            'runtime': episode.get('runtime') or series.get('averageRuntime', 48),
            'thumbnail': image_url,
            'rating': episode.get('siteRating'),
            'rating_count': episode.get('siteRatingCount'),
            'imdb_id': episode.get('imdbId'),
            'tvdb_id': episode.get('id'),
            'tvdb_series_id': series.get('tvdb_id') or series.get('id'),
            'series_name': series.get('name', ''),
            'network': series.get('network', {}).get('name') if isinstance(series.get('network'), dict) else None,
            'genres': series.get('genres', []),
        }
    
    def _normalize_tvmaze_episode(
        self,
        episode: Dict[str, Any],
        show: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize TVMaze episode data to unified format"""
        # Clean HTML from summary
        summary = episode.get('summary', '')
        if summary:
            import re
            summary = re.sub(r'<[^>]+>', '', summary)  # Remove HTML tags
        
        # Extract image URL
        image_url = None
        if episode.get('image'):
            image_url = episode['image'].get('original') or episode['image'].get('medium')
        elif show.get('image'):
            # Fallback to show image
            image_url = show['image'].get('original') or show['image'].get('medium')
        
        return {
            'source': 'tvmaze',
            'title': episode.get('name', ''),
            'description': summary,
            'season': episode.get('season'),
            'episode': episode.get('number'),
            'air_date': episode.get('airdate', ''),
            'runtime': episode.get('runtime') or show.get('averageRuntime', 48),
            'thumbnail': image_url,
            'rating': episode.get('rating', {}).get('average'),
            'tvmaze_id': episode.get('id'),
            'tvmaze_show_id': show.get('id'),
            'series_name': show.get('name', ''),
            'network': show.get('network', {}).get('name') if show.get('network') else None,
            'genres': show.get('genres', []),
        }
    
    async def get_movie_metadata(
        self,
        title: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get movie metadata from TMDB"""
        if not self.tmdb:
            return None
        
        try:
            # Search for movie
            movie = await self.tmdb.search_movie(title, year)
            if not movie:
                return None
            
            movie_id = movie.get('id')
            if not movie_id:
                return None
            
            # Get detailed information
            details = await self.tmdb.get_movie_details(movie_id)
            if not details:
                return None
            
            return self._normalize_tmdb_movie(details)
        except Exception as e:
            logger.error(f"TMDB movie metadata failed: {e}")
            return None
    
    def _normalize_tmdb_movie(self, movie: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize TMDB movie data to unified format"""
        from streamtv.utils.media_meta import normalize_cast

        # Build poster URL
        poster_url = None
        if movie.get('poster_path'):
            poster_url = f"https://image.tmdb.org/t/p/original{movie['poster_path']}"
        
        backdrop_url = None
        if movie.get('backdrop_path'):
            backdrop_url = f"https://image.tmdb.org/t/p/original{movie['backdrop_path']}"

        cast = normalize_cast(movie.get("credits") or {})
        
        return {
            'source': 'tmdb',
            'title': movie.get('title', ''),
            'original_title': movie.get('original_title', ''),
            'description': movie.get('overview', ''),
            'description_completeness': len(movie.get('overview') or ''),
            'release_date': movie.get('release_date', ''),
            'air_date': movie.get('release_date', ''),
            'runtime': movie.get('runtime'),
            'poster': poster_url,
            'thumbnail': poster_url,  # alias for MediaItem / XMLTV icon path
            'backdrop': backdrop_url,
            'rating': movie.get('vote_average'),
            'rating_count': movie.get('vote_count'),
            'imdb_id': movie.get('imdb_id'),
            'tmdb_id': movie.get('id'),
            'genres': [g['name'] for g in movie.get('genres', [])],
            'tagline': movie.get('tagline', ''),
            'budget': movie.get('budget'),
            'revenue': movie.get('revenue'),
            'production_companies': [c['name'] for c in movie.get('production_companies', [])],
            'cast': cast,
            'sources_consulted': ['tmdb'],
            'unverified': False,
        }


def create_metadata_manager(
    tvdb_api_key: Optional[str] = None,
    tvdb_read_token: Optional[str] = None,
    tmdb_api_key: Optional[str] = None,
    enable_tvdb: bool = True,
    enable_tvmaze: bool = True,
    enable_tmdb: bool = True
) -> MetadataManager:
    """
    Create a metadata manager with configured providers
    
    Args:
        tvdb_api_key: TVDB API key
        tvdb_read_token: TVDB v4 read access token (preferred)
        tmdb_api_key: TMDB API key
        enable_tvdb: Enable TVDB provider
        enable_tvmaze: Enable TVMaze provider (free fallback)
        enable_tmdb: Enable TMDB provider (for movies)
        
    Returns:
        Configured MetadataManager instance
    """
    tvdb_client = None
    if enable_tvdb and (tvdb_api_key or tvdb_read_token):
        tvdb_client = TVDBClient(
            api_key=tvdb_api_key or "",
            read_token=tvdb_read_token
        )
    
    tvmaze_client = TVMazeClient() if enable_tvmaze else None
    
    tmdb_client = None
    if enable_tmdb and tmdb_api_key:
        tmdb_client = TMDBClient(api_key=tmdb_api_key)
    
    return MetadataManager(
        tvdb_client=tvdb_client,
        tvmaze_client=tvmaze_client,
        tmdb_client=tmdb_client
    )

