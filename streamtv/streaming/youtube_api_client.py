"""YouTube Data API v3 client for metadata and validation"""

import httpx
from typing import Optional, Dict, Any, List
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class YouTubeAPIClient:
    """Client for YouTube Data API v3"""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube API client
        
        Args:
            api_key: YouTube Data API v3 key (optional, but recommended)
        """
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        try:
            parsed = urlparse(url)
            if parsed.hostname in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']:
                if parsed.path == '/watch':
                    return parse_qs(parsed.query).get('v', [None])[0]
                elif parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
                elif parsed.hostname == 'youtu.be':
                    return parsed.path[1:]
                elif parsed.path.startswith('/v/'):
                    return parsed.path.split('/')[2]
        except Exception as e:
            logger.error(f"Error extracting YouTube video ID: {e}")
        return None
    
    async def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video information from YouTube Data API v3
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video information dict or None if not found/error
        """
        if not self.api_key:
            logger.debug("YouTube API key not configured, skipping API validation")
            return None
        
        try:
            url = f"{self.BASE_URL}/videos"
            params = {
                'id': video_id,
                'part': 'snippet,contentDetails,status,statistics',
                'key': self.api_key
            }
            
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' not in data or len(data['items']) == 0:
                logger.warning(f"YouTube video {video_id} not found via API")
                return None
            
            item = data['items'][0]
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            status = item.get('status', {})
            statistics = item.get('statistics', {})
            
            # Parse duration (ISO 8601 format: PT1H2M10S)
            duration_str = content_details.get('duration', 'PT0S')
            duration_seconds = self._parse_duration(duration_str)
            
            # Check video availability
            privacy_status = status.get('privacyStatus', 'unknown')
            upload_status = status.get('uploadStatus', 'unknown')
            
            # Video is available if it's public and uploaded
            is_available = (
                privacy_status == 'public' and 
                upload_status == 'processed'
            )
            
            if not is_available:
                logger.warning(
                    f"YouTube video {video_id} not available: "
                    f"privacy={privacy_status}, upload_status={upload_status}"
                )
            
            return {
                'id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'duration': duration_seconds,
                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url') or 
                            snippet.get('thumbnails', {}).get('medium', {}).get('url') or
                            snippet.get('thumbnails', {}).get('default', {}).get('url'),
                'uploader': snippet.get('channelTitle', ''),
                'upload_date': snippet.get('publishedAt', '')[:10] if snippet.get('publishedAt') else '',
                'view_count': int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else 0,
                'is_available': is_available,
                'privacy_status': privacy_status,
                'upload_status': upload_status,
                'category_id': snippet.get('categoryId', ''),
                'tags': snippet.get('tags', []),
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error(f"YouTube API quota exceeded or API key invalid: {e}")
            elif e.response.status_code == 404:
                logger.warning(f"YouTube video {video_id} not found")
            else:
                logger.error(f"YouTube API error for {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting YouTube video info from API: {e}")
            return None
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration string to seconds"""
        import re
        duration_str = duration_str.replace('PT', '')
        hours = 0
        minutes = 0
        seconds = 0
        
        # Extract hours
        hour_match = re.search(r'(\d+)H', duration_str)
        if hour_match:
            hours = int(hour_match.group(1))
        
        # Extract minutes
        minute_match = re.search(r'(\d+)M', duration_str)
        if minute_match:
            minutes = int(minute_match.group(1))
        
        # Extract seconds
        second_match = re.search(r'(\d+)S', duration_str)
        if second_match:
            seconds = int(second_match.group(1))
        
        return hours * 3600 + minutes * 60 + seconds
    
    async def validate_video(self, url: str) -> Dict[str, Any]:
        """
        Validate YouTube video URL and get basic info
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dict with validation results:
            {
                'valid': bool,
                'video_id': str or None,
                'available': bool,
                'info': dict or None,
                'error': str or None
            }
        """
        video_id = self.extract_video_id(url)
        
        if not video_id:
            return {
                'valid': False,
                'video_id': None,
                'available': False,
                'info': None,
                'error': 'Invalid YouTube URL'
            }
        
        if not self.api_key:
            # Without API key, we can't validate, but URL is valid
            return {
                'valid': True,
                'video_id': video_id,
                'available': True,  # Assume available without API
                'info': None,
                'error': None
            }
        
        info = await self.get_video_info(video_id)
        
        if info is None:
            return {
                'valid': True,
                'video_id': video_id,
                'available': False,
                'info': None,
                'error': 'Video not found or unavailable'
            }
        
        return {
            'valid': True,
            'video_id': video_id,
            'available': info.get('is_available', False),
            'info': info,
            'error': None if info.get('is_available') else f"Video {info.get('privacy_status', 'unknown')} status"
        }
    
    async def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of video information dicts
        """
        if not self.api_key:
            logger.warning("YouTube API key not configured, cannot search")
            return []
        
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'q': query,
                'part': 'snippet',
                'type': 'video',
                'maxResults': min(max_results, 50),  # API limit is 50
                'key': self.api_key
            }
            
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                video_id = item.get('id', {}).get('videoId')
                
                if video_id:
                    results.append({
                        'id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url') or 
                                    snippet.get('thumbnails', {}).get('medium', {}).get('url'),
                        'uploader': snippet.get('channelTitle', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching YouTube videos: {e}")
            return []

