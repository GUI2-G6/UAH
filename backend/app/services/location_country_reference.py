from __future__ import annotations

import re
from functools import lru_cache

SENTINEL_COUNTRY_CODE_TO_NAME = {
    "XX": "Remote / Global",
    "XU": "Uncertain",
}

ISO_COUNTRY_CODE_TO_NAME = {
    "AD": "Andorra",
    "AE": "United Arab Emirates",
    "AF": "Afghanistan",
    "AG": "Antigua and Barbuda",
    "AI": "Anguilla",
    "AL": "Albania",
    "AM": "Armenia",
    "AO": "Angola",
    "AQ": "Antarctica",
    "AR": "Argentina",
    "AS": "American Samoa",
    "AT": "Austria",
    "AU": "Australia",
    "AW": "Aruba",
    "AX": "Aland Islands",
    "AZ": "Azerbaijan",
    "BA": "Bosnia and Herzegovina",
    "BB": "Barbados",
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BF": "Burkina Faso",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BI": "Burundi",
    "BJ": "Benin",
    "BL": "Saint Barthelemy",
    "BM": "Bermuda",
    "BN": "Brunei",
    "BO": "Bolivia",
    "BQ": "Bonaire, Sint Eustatius and Saba",
    "BR": "Brazil",
    "BS": "Bahamas",
    "BT": "Bhutan",
    "BV": "Bouvet Island",
    "BW": "Botswana",
    "BY": "Belarus",
    "BZ": "Belize",
    "CA": "Canada",
    "CC": "Cocos (Keeling) Islands",
    "CD": "Democratic Republic of the Congo",
    "CF": "Central African Republic",
    "CG": "Republic of the Congo",
    "CH": "Switzerland",
    "CI": "Cote d'Ivoire",
    "CK": "Cook Islands",
    "CL": "Chile",
    "CM": "Cameroon",
    "CN": "China",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "CU": "Cuba",
    "CV": "Cape Verde",
    "CW": "Curacao",
    "CX": "Christmas Island",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DJ": "Djibouti",
    "DK": "Denmark",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "DZ": "Algeria",
    "EC": "Ecuador",
    "EE": "Estonia",
    "EG": "Egypt",
    "EH": "Western Sahara",
    "ER": "Eritrea",
    "ES": "Spain",
    "ET": "Ethiopia",
    "FI": "Finland",
    "FJ": "Fiji",
    "FK": "Falkland Islands",
    "FM": "Micronesia",
    "FO": "Faroe Islands",
    "FR": "France",
    "GA": "Gabon",
    "GB": "United Kingdom",
    "GD": "Grenada",
    "GE": "Georgia",
    "GF": "French Guiana",
    "GG": "Guernsey",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GL": "Greenland",
    "GM": "Gambia",
    "GN": "Guinea",
    "GP": "Guadeloupe",
    "GQ": "Equatorial Guinea",
    "GR": "Greece",
    "GS": "South Georgia and the South Sandwich Islands",
    "GT": "Guatemala",
    "GU": "Guam",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HK": "Hong Kong",
    "HM": "Heard Island and McDonald Islands",
    "HN": "Honduras",
    "HR": "Croatia",
    "HT": "Haiti",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IM": "Isle of Man",
    "IN": "India",
    "IO": "British Indian Ocean Territory",
    "IQ": "Iraq",
    "IR": "Iran",
    "IS": "Iceland",
    "IT": "Italy",
    "JE": "Jersey",
    "JM": "Jamaica",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KG": "Kyrgyzstan",
    "KH": "Cambodia",
    "KI": "Kiribati",
    "KM": "Comoros",
    "KN": "Saint Kitts and Nevis",
    "KP": "North Korea",
    "KR": "South Korea",
    "KW": "Kuwait",
    "KY": "Cayman Islands",
    "KZ": "Kazakhstan",
    "LA": "Laos",
    "LB": "Lebanon",
    "LC": "Saint Lucia",
    "LI": "Liechtenstein",
    "LK": "Sri Lanka",
    "LR": "Liberia",
    "LS": "Lesotho",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "LY": "Libya",
    "MA": "Morocco",
    "MC": "Monaco",
    "MD": "Moldova",
    "ME": "Montenegro",
    "MF": "Saint Martin",
    "MG": "Madagascar",
    "MH": "Marshall Islands",
    "MK": "North Macedonia",
    "ML": "Mali",
    "MM": "Myanmar",
    "MN": "Mongolia",
    "MO": "Macao",
    "MP": "Northern Mariana Islands",
    "MQ": "Martinique",
    "MR": "Mauritania",
    "MS": "Montserrat",
    "MT": "Malta",
    "MU": "Mauritius",
    "MV": "Maldives",
    "MW": "Malawi",
    "MX": "Mexico",
    "MY": "Malaysia",
    "MZ": "Mozambique",
    "NA": "Namibia",
    "NC": "New Caledonia",
    "NE": "Niger",
    "NF": "Norfolk Island",
    "NG": "Nigeria",
    "NI": "Nicaragua",
    "NL": "Netherlands",
    "NO": "Norway",
    "NP": "Nepal",
    "NR": "Nauru",
    "NU": "Niue",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PA": "Panama",
    "PE": "Peru",
    "PF": "French Polynesia",
    "PG": "Papua New Guinea",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PM": "Saint Pierre and Miquelon",
    "PN": "Pitcairn",
    "PR": "Puerto Rico",
    "PS": "Palestine",
    "PT": "Portugal",
    "PW": "Palau",
    "PY": "Paraguay",
    "QA": "Qatar",
    "RE": "Reunion",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "RW": "Rwanda",
    "SA": "Saudi Arabia",
    "SB": "Solomon Islands",
    "SC": "Seychelles",
    "SD": "Sudan",
    "SE": "Sweden",
    "SG": "Singapore",
    "SH": "Saint Helena, Ascension and Tristan da Cunha",
    "SI": "Slovenia",
    "SJ": "Svalbard and Jan Mayen",
    "SK": "Slovakia",
    "SL": "Sierra Leone",
    "SM": "San Marino",
    "SN": "Senegal",
    "SO": "Somalia",
    "SR": "Suriname",
    "SS": "South Sudan",
    "ST": "Sao Tome and Principe",
    "SV": "El Salvador",
    "SX": "Sint Maarten",
    "SY": "Syria",
    "SZ": "Eswatini",
    "TC": "Turks and Caicos Islands",
    "TD": "Chad",
    "TF": "French Southern Territories",
    "TG": "Togo",
    "TH": "Thailand",
    "TJ": "Tajikistan",
    "TK": "Tokelau",
    "TL": "Timor-Leste",
    "TM": "Turkmenistan",
    "TN": "Tunisia",
    "TO": "Tonga",
    "TR": "Turkey",
    "TT": "Trinidad and Tobago",
    "TV": "Tuvalu",
    "TW": "Taiwan",
    "TZ": "Tanzania",
    "UA": "Ukraine",
    "UG": "Uganda",
    "UM": "United States Minor Outlying Islands",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VA": "Vatican City",
    "VC": "Saint Vincent and the Grenadines",
    "VE": "Venezuela",
    "VG": "British Virgin Islands",
    "VI": "U.S. Virgin Islands",
    "VN": "Vietnam",
    "VU": "Vanuatu",
    "WF": "Wallis and Futuna",
    "WS": "Samoa",
    "YE": "Yemen",
    "YT": "Mayotte",
    "ZA": "South Africa",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

COUNTRY_CODE_TO_NAME = {
    **ISO_COUNTRY_CODE_TO_NAME,
    **SENTINEL_COUNTRY_CODE_TO_NAME,
}

REAL_COUNTRY_CODES = frozenset(ISO_COUNTRY_CODE_TO_NAME)
NON_SELECTABLE_COUNTRY_CODES = frozenset(SENTINEL_COUNTRY_CODE_TO_NAME)

COUNTRY_ALIASES = {
    "uk": "GB",
    "u.k.": "GB",
    "great britain": "GB",
    "britain": "GB",
    "usa": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "uae": "AE",
    "u.a.e.": "AE",
    "dr congo": "CD",
    "drc": "CD",
    "congo-kinshasa": "CD",
    "congo-brazzaville": "CG",
    "ivory coast": "CI",
    "cote divoire": "CI",
    "cape verde": "CV",
    "cabo verde": "CV",
    "czech republic": "CZ",
    "south korea": "KR",
    "republic of korea": "KR",
    "korea, south": "KR",
    "north korea": "KP",
    "democratic people's republic of korea": "KP",
    "russia": "RU",
    "russian federation": "RU",
    "moldova": "MD",
    "republic of moldova": "MD",
    "bolivia": "BO",
    "venezuela": "VE",
    "iran": "IR",
    "lao pdr": "LA",
    "viet nam": "VN",
    "syria": "SY",
    "syrian arab republic": "SY",
    "taiwan, province of china": "TW",
    "palestinian territories": "PS",
    "palestinian territory": "PS",
    "palestine state": "PS",
    "brunei darussalam": "BN",
    "micronesia, federated states of": "FM",
    "north macedonia": "MK",
    "myanmar (burma)": "MM",
    "tanzania": "TZ",
    "united states of america": "US",
    "deutschland": "DE",
    "espana": "ES",
    "suisse": "CH",
    "suomi": "FI",
    "osterreich": "AT",
    "republique francaise": "FR",
    "the netherlands": "NL",
    "holland": "NL",
}

COUNTRY_NAME_TO_CODE = {
    **{name.lower(): code for code, name in ISO_COUNTRY_CODE_TO_NAME.items()},
    **{code.lower(): code for code in ISO_COUNTRY_CODE_TO_NAME},
    **COUNTRY_ALIASES,
}

US_STATE_CODE_TO_NAME = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
US_STATE_CODES = frozenset(US_STATE_CODE_TO_NAME)
US_STATE_NAME_TO_CODE = {name.lower(): code for code, name in US_STATE_CODE_TO_NAME.items()}

CA_PROVINCE_CODE_TO_NAME = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}
CA_PROVINCE_CODES = frozenset(CA_PROVINCE_CODE_TO_NAME)
CA_PROVINCE_NAME_TO_CODE = {name.lower(): code for code, name in CA_PROVINCE_CODE_TO_NAME.items()}

AU_STATE_CODE_TO_NAME = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "SA": "South Australia",
    "WA": "Western Australia",
    "TAS": "Tasmania",
    "ACT": "Australian Capital Territory",
    "NT": "Northern Territory",
}
AU_STATE_CODES = frozenset(AU_STATE_CODE_TO_NAME)
AU_STATE_NAME_TO_CODE = {name.lower(): code for code, name in AU_STATE_CODE_TO_NAME.items()}

OTHER_REGION_CODE_TO_COUNTRY = {
    "ENG": "GB",
    "SCT": "GB",
    "WLS": "GB",
    "NIR": "GB",
    "DXB": "AE",
    "JKT": "ID",
}

OTHER_REGION_NAME_TO_COUNTRY = {
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "manila metro": "PH",
    "metro manila": "PH",
    "national capital region": "PH",
    "dubai": "AE",
}

SPECIAL_LOCALITY_TO_COUNTRY = {
    "washington dc": "US",
    "district of columbia": "US",
    "new york city": "US",
    "nyc": "US",
    "manhattan": "US",
    "brooklyn": "US",
    "bronx": "US",
    "queens": "US",
    "staten island": "US",
    "grand central": "US",
}

COUNTRY_TLD_TO_CODE = {
    ".au": "AU",
    ".br": "BR",
    ".ca": "CA",
    ".co.uk": "GB",
    ".de": "DE",
    ".fr": "FR",
    ".ie": "IE",
    ".in": "IN",
    ".jp": "JP",
    ".kr": "KR",
    ".mx": "MX",
    ".nl": "NL",
    ".nz": "NZ",
    ".ph": "PH",
    ".pl": "PL",
    ".sg": "SG",
    ".uk": "GB",
    ".us": "US",
}

COUNTRY_CLUE_PATTERNS = (
    ("CA", re.compile(r"\b(?:cad|c\$)\b", re.IGNORECASE)),
    ("AU", re.compile(r"\b(?:aud|a\$)\b", re.IGNORECASE)),
    ("NZ", re.compile(r"\b(?:nzd|nz\$)\b", re.IGNORECASE)),
    ("GB", re.compile(r"(?:\bgbp\b|\bpounds?\b|£)", re.IGNORECASE)),
    ("JP", re.compile(r"(?:\bjpy\b|\byen\b)", re.IGNORECASE)),
    ("KR", re.compile(r"(?:\bkrw\b|\bwon\b)", re.IGNORECASE)),
    ("PH", re.compile(r"(?:\bphp\b|\bpeso\b)", re.IGNORECASE)),
    ("DE", re.compile(r"\bbundesland\b", re.IGNORECASE)),
    ("JP", re.compile(r"\bprefecture\b", re.IGNORECASE)),
)

POSTAL_PATTERNS = (
    ("US", re.compile(r"\b\d{5}(?:-\d{4})?\b")),
    ("CA", re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\s?\d[ABCEGHJ-NPRSTV-Z]\d\b", re.IGNORECASE)),
    ("GB", re.compile(r"\b(?:GIR\s?0AA|[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b", re.IGNORECASE)),
    ("AU", re.compile(r"\b\d{4}\b")),
    ("DE", re.compile(r"\b\d{5}\b")),
)

PROVIDER_COUNTRY_PRIORS = {}

_PUNCTUATION_RE = re.compile(r"[^a-z0-9]+")


def is_real_country_code(value: str | None) -> bool:
    normalized = " ".join((value or "").strip().upper().split())
    return normalized in REAL_COUNTRY_CODES


def is_sentinel_country_code(value: str | None) -> bool:
    normalized = " ".join((value or "").strip().upper().split())
    return normalized in SENTINEL_COUNTRY_CODE_TO_NAME


def normalize_country_name_key(value: str | None) -> str:
    normalized = " ".join((value or "").strip().lower().split())
    normalized = normalized.replace("&", " and ")
    return " ".join(_PUNCTUATION_RE.sub(" ", normalized).split())


def country_name_from_code(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().upper().split())
    if not normalized:
        return None
    return COUNTRY_CODE_TO_NAME.get(normalized)


def region_country_from_piece(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().split())
    if not normalized:
        return None

    upper = normalized.upper()
    if upper in US_STATE_CODES:
        return "US"
    if upper in CA_PROVINCE_CODES:
        return "CA"
    if upper in AU_STATE_CODES:
        return "AU"
    if upper in OTHER_REGION_CODE_TO_COUNTRY:
        return OTHER_REGION_CODE_TO_COUNTRY[upper]

    key = normalize_country_name_key(normalized)
    if key in US_STATE_NAME_TO_CODE:
        return "US"
    if key in CA_PROVINCE_NAME_TO_CODE:
        return "CA"
    if key in AU_STATE_NAME_TO_CODE:
        return "AU"
    return OTHER_REGION_NAME_TO_COUNTRY.get(key)


@lru_cache(maxsize=1)
def searchable_country_phrases() -> tuple[tuple[str, str], ...]:
    phrases: dict[str, str] = {}
    for alias, code in COUNTRY_NAME_TO_CODE.items():
        if len(alias) <= 2:
            continue
        phrases[normalize_country_name_key(alias)] = code
    return tuple(sorted(phrases.items(), key=lambda item: (-len(item[0]), item[0])))
