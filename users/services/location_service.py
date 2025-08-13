import requests
import pycountry
from django.core.cache import cache
from django.conf import settings
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class LocationService:
    """
    Service for fetching comprehensive country and city data from multiple sources:
    1. REST Countries API - For complete country data
    2. GeoNames API - For cities and towns worldwide
    3. pycountry - As fallback for country data
    """
    
    def __init__(self):
        self.rest_countries_url = getattr(settings, 'REST_COUNTRIES_API_URL', 'https://restcountries.com/v3.1')
        self.geonames_url = getattr(settings, 'GEONAMES_API_URL', 'http://api.geonames.org')
        self.geonames_username = getattr(settings, 'GEONAMES_USERNAME', 'demo')
        self.cache_timeout = getattr(settings, 'LOCATION_CACHE_TIMEOUT', 60 * 60 * 24)
    
    def get_all_countries(self, filter_type: str = 'all', search: str = '') -> List[Dict]:
        """
        Get all countries from REST Countries API with fallback to pycountry
        """
        cache_key = f"countries_{filter_type}_{search}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Try REST Countries API first
            countries = self._fetch_from_rest_countries()
        except Exception as e:
            logger.warning(f"REST Countries API failed: {e}. Using pycountry fallback.")
            countries = self._fetch_from_pycountry()
        
        # Apply filters
        if filter_type == 'popular':
            countries = self._filter_popular_countries(countries)
        elif filter_type == 'muslim_majority':
            countries = self._filter_muslim_majority_countries(countries)
        
        # Apply search
        if search:
            countries = self._search_countries(countries, search)
        
        # Cache the result
        cache.set(cache_key, countries, self.cache_timeout)
        return countries
    
    def get_cities_for_country(self, country_code: str, search: str = '', limit: int = 100) -> List[Dict]:
        """
        Get cities for a country from GeoNames API
        """
        cache_key = f"cities_{country_code}_{search}_{limit}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            cities = self._fetch_cities_from_geonames(country_code, search, limit)
        except Exception as e:
            logger.error(f"GeoNames API failed for {country_code}: {e}")
            cities = self._get_fallback_cities(country_code)
        
        # Cache the result
        cache.set(cache_key, cities, self.cache_timeout)
        return cities
    
    def _fetch_from_rest_countries(self) -> List[Dict]:
        """Fetch all countries from REST Countries API"""
        url = f"{self.rest_countries_url}/all"
        params = {
            'fields': 'name,cca2,cca3,flag,region,subregion,population,capital,callingCodes,timezones'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        countries_data = response.json()
        countries = []
        
        for country in countries_data:
            try:
                # Extract calling code (handle different formats)
                calling_codes = country.get('idd', {})
                calling_code = ''
                if calling_codes.get('root') and calling_codes.get('suffixes'):
                    root = calling_codes['root']
                    suffix = calling_codes['suffixes'][0] if calling_codes['suffixes'] else ''
                    calling_code = f"{root}{suffix}"
                
                countries.append({
                    'code': country['cca2'],
                    'code3': country.get('cca3', ''),
                    'name': country['name']['common'],
                    'official_name': country['name'].get('official', ''),
                    'calling_code': calling_code,
                    'region': country.get('region', ''),
                    'subregion': country.get('subregion', ''),
                    'population': country.get('population', 0),
                    'capital': country.get('capital', [''])[0] if country.get('capital') else '',
                    'flag': country.get('flag', ''),
                    'timezones': country.get('timezones', [])
                })
            except (KeyError, IndexError) as e:
                logger.warning(f"Error processing country {country}: {e}")
                continue
        
        return sorted(countries, key=lambda x: x['name'])
    
    def _fetch_from_pycountry(self) -> List[Dict]:
        """Fallback: Get countries from pycountry library"""
        countries = []
        
        for country in pycountry.countries:
            countries.append({
                'code': country.alpha_2,
                'code3': country.alpha_3,
                'name': country.name,
                'official_name': getattr(country, 'official_name', country.name),
                'calling_code': '',  # Not available in pycountry
                'region': '',  # Not available in pycountry
                'subregion': '',
                'population': 0,
                'capital': '',
                'flag': '',
                'timezones': []
            })
        
        return sorted(countries, key=lambda x: x['name'])
    
    def _fetch_cities_from_geonames(self, country_code: str, search: str = '', limit: int = 100) -> List[Dict]:
        """Fetch cities from GeoNames API"""
        url = f"{self.geonames_url}/searchJSON"
        
        params = {
            'country': country_code,
            'featureClass': 'P',  # Populated places (cities, towns, villages)
            'maxRows': min(limit, 1000),  # GeoNames API limit
            'orderby': 'population',
            'username': self.geonames_username,
            'style': 'FULL'
        }
        
        if search:
            params['name_startsWith'] = search
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if 'geonames' not in data:
            raise Exception(f"Invalid response from GeoNames API: {data}")
        
        cities = []
        for city in data['geonames']:
            try:
                cities.append({
                    'name': city['name'],
                    'admin1': city.get('adminName1', ''),  # State/Province
                    'admin2': city.get('adminName2', ''),  # County/District
                    'population': int(city.get('population', 0)),
                    'latitude': float(city.get('lat', 0)),
                    'longitude': float(city.get('lng', 0)),
                    'timezone': city.get('timezone', {}).get('timeZoneId', ''),
                    'feature_code': city.get('fcode', ''),
                    'is_capital': city.get('fcode') == 'PPLC',  # Capital city
                    'geoname_id': city.get('geonameId', 0)
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing city {city}: {e}")
                continue
        
        return cities
    
    def _get_fallback_cities(self, country_code: str) -> List[Dict]:
        """Fallback cities for major countries when API fails"""
        fallback_data = {
            'NG': [
                {'name': 'Lagos', 'admin1': 'Lagos', 'population': 15000000, 'is_capital': False},
                {'name': 'Abuja', 'admin1': 'FCT', 'population': 3000000, 'is_capital': True},
                {'name': 'Kano', 'admin1': 'Kano', 'population': 4000000, 'is_capital': False},
                {'name': 'Ibadan', 'admin1': 'Oyo', 'population': 3500000, 'is_capital': False},
                {'name': 'Port Harcourt', 'admin1': 'Rivers', 'population': 2000000, 'is_capital': False},
            ],
            'US': [
                {'name': 'New York', 'admin1': 'New York', 'population': 8500000, 'is_capital': False},
                {'name': 'Los Angeles', 'admin1': 'California', 'population': 4000000, 'is_capital': False},
                {'name': 'Chicago', 'admin1': 'Illinois', 'population': 2700000, 'is_capital': False},
                {'name': 'Houston', 'admin1': 'Texas', 'population': 2300000, 'is_capital': False},
                {'name': 'Washington', 'admin1': 'DC', 'population': 700000, 'is_capital': True},
            ],
            'GB': [
                {'name': 'London', 'admin1': 'England', 'population': 9000000, 'is_capital': True},
                {'name': 'Birmingham', 'admin1': 'England', 'population': 2600000, 'is_capital': False},
                {'name': 'Manchester', 'admin1': 'England', 'population': 2700000, 'is_capital': False},
                {'name': 'Glasgow', 'admin1': 'Scotland', 'population': 1700000, 'is_capital': False},
            ]
        }
        
        cities = fallback_data.get(country_code, [])
        
        # Add missing fields for consistency
        for city in cities:
            city.setdefault('admin2', '')
            city.setdefault('latitude', 0)
            city.setdefault('longitude', 0)
            city.setdefault('timezone', '')
            city.setdefault('feature_code', '')
            city.setdefault('geoname_id', 0)
        
        return cities
    
    def _filter_popular_countries(self, countries: List[Dict]) -> List[Dict]:
        """Filter to popular countries commonly used in signup"""
        popular_codes = {
            'US', 'GB', 'CA', 'AU', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE',  # Western
            'NG', 'GH', 'KE', 'ZA', 'EG', 'MA', 'TZ', 'UG', 'ET', 'SN',  # African
            'SA', 'AE', 'TR', 'EG', 'JO', 'LB', 'KW', 'QA', 'BH', 'OM',  # Middle East
            'PK', 'BD', 'IN', 'ID', 'MY', 'SG', 'TH', 'PH', 'VN', 'JP',  # Asian
            'BR', 'MX', 'AR', 'CO', 'PE', 'CL'  # Latin America
        }
        return [c for c in countries if c['code'] in popular_codes]
    
    def _filter_muslim_majority_countries(self, countries: List[Dict]) -> List[Dict]:
        """Filter to Muslim-majority countries"""
        muslim_codes = {
            'AF', 'DZ', 'AZ', 'BH', 'BD', 'BN', 'KM', 'DJ', 'EG', 'GM', 'GN', 'GW',
            'ID', 'IR', 'IQ', 'JO', 'KZ', 'XK', 'KW', 'KG', 'LB', 'LY', 'MV', 'ML',
            'MR', 'MA', 'NE', 'NG', 'OM', 'PK', 'PS', 'QA', 'SA', 'SN', 'SL', 'SO',
            'SD', 'SY', 'TJ', 'TN', 'TR', 'TM', 'AE', 'UZ', 'EH', 'YE'
        }
        return [c for c in countries if c['code'] in muslim_codes]
    
    def _search_countries(self, countries: List[Dict], search: str) -> List[Dict]:
        """Search countries by name or code"""
        search_lower = search.lower()
        return [
            country for country in countries
            if (search_lower in country['name'].lower() or 
                search_lower in country['code'].lower() or
                search_lower in country.get('official_name', '').lower())
        ]
