"""Plex Media Server API client for EPG and DVR functionality"""

import httpx
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class PlexAPIClient:
    """Client for Plex Media Server API"""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        """
        Initialize Plex API client
        
        Args:
            base_url: Plex Media Server base URL (e.g., "http://192.168.1.100:32400")
            token: Plex authentication token (optional but recommended)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            'Accept': 'application/xml',  # Plex returns XML by default
            'X-Plex-Product': 'StreamTV',
            'X-Plex-Version': '1.0.0',
            'X-Plex-Client-Identifier': 'streamtv-epg-client'
        }
        if self.token:
            headers['X-Plex-Token'] = self.token
        return headers
    
    async def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get Plex Media Server information"""
        try:
            url = f"{self.base_url}/"
            response = await self._client.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            # Plex returns XML by default
            response_text = response.text
            # Handle potential BOM or encoding issues
            if response_text.startswith('\ufeff'):
                response_text = response_text[1:]  # Remove BOM if present
            
            root = ET.fromstring(response_text)
            return {
                'friendlyName': root.get('friendlyName', ''),
                'machineIdentifier': root.get('machineIdentifier', ''),
                'version': root.get('version', '')
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error(f"Plex authentication failed: 401 Unauthorized")
                raise ValueError("Authentication failed. Plex token is invalid or expired.")
            elif e.response.status_code == 404:
                logger.error(f"Plex server not found: 404")
                raise ValueError(f"Plex server not found at {self.base_url}")
            else:
                logger.error(f"Plex HTTP error {e.response.status_code}: {e.response.text[:200]}")
                raise ValueError(f"HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except httpx.ConnectError as e:
            logger.error(f"Could not connect to Plex server at {self.base_url}: {e}")
            raise ValueError(f"Could not connect to {self.base_url}. Check if server is running and URL is correct.")
        except httpx.TimeoutException:
            logger.error(f"Connection to Plex server timed out: {self.base_url}")
            raise ValueError(f"Connection to {self.base_url} timed out. Server may be unreachable.")
        except ET.ParseError as e:
            logger.error(f"Failed to parse Plex server response: {e}")
            raise ValueError("Plex server returned invalid XML. Server may not be a valid Plex Media Server.")
        except Exception as e:
            logger.error(f"Error getting Plex server info: {e}", exc_info=True)
            raise ValueError(f"Connection error: {str(e)}")
    
    async def get_dvrs(self) -> List[Dict[str, Any]]:
        """
        Get all DVRs from Plex
        
        Reference: https://developer.plex.tv/pms/#tag/DVR/operation/getGetDVRs
        """
        try:
            url = f"{self.base_url}/livetv/dvrs"
            response = await self._client.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            dvrs = []
            for dvr_elem in root.findall('.//Dvr'):
                dvrs.append({
                    'id': dvr_elem.get('key', ''),
                    'title': dvr_elem.get('title', ''),
                    'enabled': dvr_elem.get('enabled', 'false') == 'true'
                })
            return dvrs
        except Exception as e:
            logger.error(f"Error getting Plex DVRs: {e}")
            return []
    
    async def get_channels_for_lineup(self, lineup_id: str) -> List[Dict[str, Any]]:
        """
        Get channels for a lineup
        
        Reference: https://developer.plex.tv/pms/#tag/EPG/operation/getGetChannelsForALineup
        """
        try:
            url = f"{self.base_url}/livetv/dvrs/epg/channels"
            params = {'lineup': lineup_id}
            response = await self._client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            channels = []
            for channel_elem in root.findall('.//Channel'):
                channels.append({
                    'id': channel_elem.get('key', ''),
                    'number': channel_elem.get('number', ''),
                    'name': channel_elem.get('title', ''),
                    'callSign': channel_elem.get('callSign', ''),
                    'icon': channel_elem.get('icon', '')
                })
            return channels
        except Exception as e:
            logger.error(f"Error getting channels for lineup {lineup_id}: {e}")
            return []
    
    async def get_lineups_for_country(self, country: str, postal_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get lineups for a country
        
        Reference: https://developer.plex.tv/pms/#tag/EPG/operation/getGetLineupsForACountryViaPostalCode
        """
        try:
            if postal_code:
                url = f"{self.base_url}/livetv/dvrs/epg/lineups"
                params = {'country': country, 'postalCode': postal_code}
            else:
                url = f"{self.base_url}/livetv/dvrs/epg/lineups"
                params = {'country': country}
            
            response = await self._client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            lineups = []
            for lineup_elem in root.findall('.//Lineup'):
                lineups.append({
                    'id': lineup_elem.get('id', ''),
                    'name': lineup_elem.get('name', ''),
                    'type': lineup_elem.get('type', ''),
                    'location': lineup_elem.get('location', '')
                })
            return lineups
        except Exception as e:
            logger.error(f"Error getting lineups for country {country}: {e}")
            return []
    
    async def get_countries(self) -> List[str]:
        """
        Get all available countries
        
        Reference: https://developer.plex.tv/pms/#tag/EPG/operation/getGetAllCountries
        """
        try:
            url = f"{self.base_url}/livetv/dvrs/epg/countries"
            response = await self._client.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            countries = []
            for country_elem in root.findall('.//Country'):
                countries.append(country_elem.get('code', ''))
            return countries
        except Exception as e:
            logger.error(f"Error getting countries: {e}")
            return []
    
    async def compute_best_channel_map(self, channel_numbers: List[str], lineup_id: str) -> Dict[str, str]:
        """
        Compute the best channel map for given channel numbers
        
        Reference: https://developer.plex.tv/pms/#tag/EPG/operation/getComputeTheBestChannelMap
        """
        try:
            url = f"{self.base_url}/livetv/dvrs/epg/channelMap"
            params = {
                'lineup': lineup_id,
                'channels': ','.join(channel_numbers)
            }
            response = await self._client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            channel_map = {}
            for mapping_elem in root.findall('.//Mapping'):
                channel_map[mapping_elem.get('number', '')] = mapping_elem.get('epgId', '')
            return channel_map
        except Exception as e:
            logger.error(f"Error computing channel map: {e}")
            return {}
    
    async def get_epg_data(self, channel_id: str, start_time: Optional[datetime] = None, 
                          end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get EPG data for a channel
        
        This is a helper method that uses Plex's DVR API to get program guide data
        """
        try:
            # Plex EPG data is typically accessed through the DVR API
            # For now, we'll return empty as Plex EPG integration requires DVR setup
            # This can be enhanced when a Plex DVR is configured
            logger.debug(f"EPG data request for channel {channel_id} (Plex EPG requires DVR setup)")
            return []
        except Exception as e:
            logger.error(f"Error getting EPG data from Plex: {e}")
            return []

