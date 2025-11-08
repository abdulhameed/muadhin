"""
Country name to ISO 3166-1 alpha-2 code conversion utility
"""

COUNTRY_NAME_TO_CODE = {
    # Common formats for countries we support
    'nigeria': 'NG',
    'ng': 'NG',

    # Other African countries
    'kenya': 'KE',
    'ke': 'KE',
    'uganda': 'UG',
    'ug': 'UG',
    'tanzania': 'TZ',
    'tz': 'TZ',
    'rwanda': 'RW',
    'rw': 'RW',
    'malawi': 'MW',
    'mw': 'MW',
    'zambia': 'ZM',
    'zm': 'ZM',
    'ghana': 'GH',
    'gh': 'GH',
    'cameroon': 'CM',
    'cm': 'CM',
    'senegal': 'SN',
    'sn': 'SN',

    # Global countries
    'united states': 'US',
    'us': 'US',
    'usa': 'US',
    'united kingdom': 'GB',
    'uk': 'GB',
    'gb': 'GB',
    'canada': 'CA',
    'ca': 'CA',
    'australia': 'AU',
    'au': 'AU',
    'india': 'IN',
    'in': 'IN',
    'germany': 'DE',
    'de': 'DE',
    'france': 'FR',
    'fr': 'FR',
    'saudi arabia': 'SA',
    'sa': 'SA',
    'uae': 'AE',
    'ae': 'AE',
    'united arab emirates': 'AE',
    'qatar': 'QA',
    'qa': 'QA',
}


def get_country_code(country: str) -> str:
    """
    Convert country name or partial code to ISO 3166-1 alpha-2 code.

    Args:
        country: Country name, code, or partial identifier

    Returns:
        2-letter ISO country code (defaults to 'NG' for Nigeria-first strategy)

    Examples:
        >>> get_country_code('NIGERIA')
        'NG'
        >>> get_country_code('Nigeria')
        'NG'
        >>> get_country_code('NG')
        'NG'
        >>> get_country_code('United States')
        'US'
    """
    if not country:
        return 'NG'  # Default to Nigeria (our primary market)

    # Normalize the input
    country_normalized = country.strip().lower()

    # Check if it's already a valid 2-letter code
    if len(country_normalized) == 2 and country_normalized.upper() in [
        'NG', 'KE', 'UG', 'TZ', 'RW', 'MW', 'ZM', 'GH', 'CM', 'SN',
        'US', 'GB', 'CA', 'AU', 'IN', 'DE', 'FR', 'SA', 'AE', 'QA'
    ]:
        return country_normalized.upper()

    # Look up in mapping
    code = COUNTRY_NAME_TO_CODE.get(country_normalized)
    if code:
        return code

    # Try to extract phone country code if starts with +
    if country.startswith('+'):
        phone_country_map = {
            '+234': 'NG',  # Nigeria
            '+254': 'KE',  # Kenya
            '+256': 'UG',  # Uganda
            '+255': 'TZ',  # Tanzania
            '+250': 'RW',  # Rwanda
            '+265': 'MW',  # Malawi
            '+260': 'ZM',  # Zambia
            '+233': 'GH',  # Ghana
            '+237': 'CM',  # Cameroon
            '+221': 'SN',  # Senegal
            '+1': 'US',    # US/Canada
            '+44': 'GB',   # UK
            '+91': 'IN',   # India
            '+49': 'DE',   # Germany
            '+33': 'FR',   # France
            '+966': 'SA',  # Saudi Arabia
            '+971': 'AE',  # UAE
            '+974': 'QA',  # Qatar
        }
        for prefix, code in phone_country_map.items():
            if country.startswith(prefix):
                return code

    # Default to Nigeria (primary market)
    return 'NG'
