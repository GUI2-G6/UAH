"""
rule_parser.py - Pure-Python Rule-Based Resume Parser (v2)
==========================================================
Extracts structured resume data from OCR markdown using:
  - Markdown pre-processing (clean OCR artifacts, HTML tables, image refs)
  - Section detection via header/keyword matching
  - Regex patterns for contact info, dates, GPA, skills
  - Heuristic name extraction (first prominent text line)
  - US cities/states lookup for location inference
  - Smart education grouping (multi-line entry merging)
  - HTML table -> text conversion for skills sections

Zero external dependencies beyond Python stdlib.
Runs on any machine, any Python 3.8+, no GPU, no API calls.

Usage:
    from rule_parser import parse_resume_markdown
    structured = parse_resume_markdown(md_text)
"""

import re
import json
from html.parser import HTMLParser

# ============================================================
# Section header patterns — order matters (first match wins)
# ============================================================
SECTION_PATTERNS = {
    "education": re.compile(
        r'^#{0,4}\s*(?:education|academic\s*background|academic\s*history'
        r'|educational\s*background|academic\s*qualifications)',
        re.IGNORECASE | re.MULTILINE
    ),
    "work_experience": re.compile(
        r'^#{0,4}\s*(?:experience|work\s*experience|professional\s*experience'
        r'|employment|employment\s*history|work\s*history|professional\s*background'
        r'|relevant\s*experience|related\s*experience|clinical\s*experience'
        r'|internship|practicum)',
        re.IGNORECASE | re.MULTILINE
    ),
    "skills": re.compile(
        r'^#{0,4}\s*(?:skills|technical\s*skills|core\s*competencies|competencies'
        r'|areas?\s*of\s*expertise|proficiencies|computer\s*skills'
        r'|software\s+skills|technologies\s+(?:used|known|&|and)|qualifications\s*summary'
        r'|skills\s*(?:and|&)\s*(?:awards?|tools|technologies))',
        re.IGNORECASE | re.MULTILINE
    ),
    "projects": re.compile(
        r'^#{0,4}\s*(?:projects|personal\s*projects|academic\s*projects'
        r'|selected\s*projects|key\s*projects|research\s*(?:projects|experience|interests)?)\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "certifications": re.compile(
        r'^#{0,4}\s*(?:certifications?|licenses?\s*(?:&|and)?\s*certifications?'
        r'|licenses?|professional\s*development'
        r'|training|credentials)\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "awards": re.compile(
        r'^#{0,4}\s*(?:awards?|honors?\s*(?:and|&)\s*awards?'
        r'|achievements?|recognition)\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "activities": re.compile(
        r'^#{0,4}\s*(?:activities|extracurricular|clubs?|organizations?'
        r'|leadership|involvement|memberships?|affiliations?)\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "volunteer": re.compile(
        r'^#{0,4}\s*(?:volunteer|community\s*(?:service|involvement)'
        r'|service|civic)',
        re.IGNORECASE | re.MULTILINE
    ),
    "summary": re.compile(
        r'^#{0,4}\s*(?:summary|objective|profile|professional\s*summary'
        r'|career\s*objective|about\s*me|overview)',
        re.IGNORECASE | re.MULTILINE
    ),
    "coursework": re.compile(
        r'^#{1,4}\s*(?:relevant\s*coursework|coursework|related\s*coursework'
        r'|relevant\s*courses)',
        re.IGNORECASE | re.MULTILINE
    ),
}

# Contact regex patterns
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE_RE = re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
LINKEDIN_RE = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?', re.IGNORECASE)
URL_RE = re.compile(r'https?://[\w./\-?=&#%]+')
GITHUB_RE = re.compile(r'(?:https?://)?(?:www\.)?github\.com/[\w-]+/?', re.IGNORECASE)

# Date patterns
# End-date tokens the range regex should accept
_END_DATE_ALTS = (
    r'[Pp]resent|[Cc]urrent|[Oo]ngoing|[Nn]ow'
    r'|[Ee]xpected|[Aa]nticipated|[Pp]rojected'
    r'|[Ii]n[- ]?[Pp]rogress'
)

DATE_RANGE_RE = re.compile(
    r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
    r'|Dec(?:ember)?)\s+)?\d{4}'
    r'\s*[-\u2013\u2014to]+\s*'
    r'(?:(?:' + _END_DATE_ALTS + r')\s+)?'  # optional expected/anticipated prefix
    r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
    r'|Dec(?:ember)?)\s+)?(?:\d{4}|' + _END_DATE_ALTS + r')',
    re.IGNORECASE
)

SINGLE_DATE_RE = re.compile(
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
    r'|Dec(?:ember)?)\s+\d{4}',
    re.IGNORECASE
)

YEAR_RANGE_RE = re.compile(
    r'\b(\d{4})\s*[-\u2013\u2014]\s*'
    r'(\d{4}|[Pp]resent|[Cc]urrent|[Oo]ngoing|[Ee]xpected|[Aa]nticipated|[Ii]n[- ]?[Pp]rogress)\b'
)

# Standalone date line: just a date/range on its own line
DATE_LINE_RE = re.compile(
    r'^\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
    r'|Dec(?:ember)?)\s+)?\d{4}'
    r'(?:\s*[-\u2013\u2014]\s*'
    r'(?:(?:' + _END_DATE_ALTS + r')\s+)?'
    r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
    r'|Dec(?:ember)?)\s+)?(?:\d{4}|' + _END_DATE_ALTS + r'))?'
    r'\s*$',
    re.IGNORECASE
)

GPA_RE = re.compile(r'(?:GPA|G\.P\.A\.?)\s*:?\s*(\d+\.\d+)\s*/?\s*(\d+\.\d+)?', re.IGNORECASE)
GPA_STANDALONE_RE = re.compile(r'\b(\d\.\d{1,2})\s*/\s*(\d\.\d{1,2})\b')

# Degree patterns — specific to avoid false matches
DEGREE_FULL_RE = re.compile(
    r'(?:Bachelor\s+of\s+(?:Science|Arts|Engineering|Fine\s+Arts|Business|Music)'
    r'|Master\s+of\s+(?:Science|Arts|Business|Public|Social|Education|Fine\s+Arts)'
    r'|Doctor\s+of\s+(?:Philosophy|Education|Medicine)'
    r'|Associate\s+of\s+(?:Science|Arts|Applied\s+Science)'
    r'|High\s+School\s+Diploma)',
    re.IGNORECASE
)

DEGREE_ABBREV_RE = re.compile(
    r'\b(?:Ph\.?D\.?|M\.?B\.?A\.?|M\.?S\.?|B\.?S\.?|B\.?A\.?|M\.?A\.?|A\.?S\.?|A\.?A\.?)\b'
)

# State abbreviations that collide with degree abbreviations
_DEGREE_STATE_COLLISIONS = {'MA', 'PA', 'AS', 'IN', 'MS'}


def _has_degree(text):
    """Check if text contains a degree keyword (full or abbreviated).
    Avoids false positives from US state abbreviations like 'MA' after commas.
    """
    if DEGREE_FULL_RE.search(text):
        return True
    m = DEGREE_ABBREV_RE.search(text)
    if m:
        abbrev = m.group(0).upper().replace('.', '')
        if abbrev in _DEGREE_STATE_COLLISIONS:
            # Check context: if preceded by ", " it's likely a state
            start = m.start()
            if start >= 2 and text[start-2:start] == ', ':
                return False
            # If surrounded by other text suggesting a degree, still True
        return True
    return False


def _extract_degree(text):
    """Extract degree string from text."""
    m = DEGREE_FULL_RE.search(text)
    if m:
        return m.group(0).strip()
    m = DEGREE_ABBREV_RE.search(text)
    if m:
        abbrev = m.group(0).upper().replace('.', '')
        if abbrev in _DEGREE_STATE_COLLISIONS:
            start = m.start()
            if start >= 2 and text[start-2:start] == ', ':
                return None
        return m.group(0).strip()
    return None
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
}
STATE_ABBREVS = set(US_STATES.keys())
STATE_NAMES = {v.lower(): k for k, v in US_STATES.items()}

# City, State pattern
CITY_STATE_RE = re.compile(
    r'([A-Z][a-zA-Z ]+),\s*('
    + '|'.join(list(STATE_ABBREVS) + [re.escape(s) for s in US_STATES.values()])
    + r')\b',
    re.IGNORECASE
)

ADDRESS_ZIP_RE = re.compile(r'(\d{5}(?:-\d{4})?)')

# Month normalizer
MONTH_MAP = {
    'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
    'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
    'sep': 'September', 'sept': 'September', 'oct': 'October',
    'nov': 'November', 'dec': 'December',
    'january': 'January', 'february': 'February', 'march': 'March',
    'april': 'April', 'june': 'June', 'july': 'July', 'august': 'August',
    'september': 'September', 'october': 'October', 'november': 'November',
    'december': 'December',
}


# ============================================================
# HTML Table Parser
# ============================================================

class TableParser(HTMLParser):
    """Extract rows from HTML tables into [[col1, col2, ...], ...]."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self._current_row = []
        self._current_cell = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self._current_row = []
        elif tag in ('td', 'th'):
            self._current_cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ('td', 'th'):
            self._in_cell = False
            self._current_row.append(''.join(self._current_cell).strip())
        elif tag == 'tr':
            if self._current_row:
                self.rows.append(self._current_row)

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell.append(data)

    def handle_entityref(self, name):
        if self._in_cell:
            entities = {'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"'}
            self._current_cell.append(entities.get(name, f'&{name};'))


def parse_html_table(html):
    """Parse an HTML table string into rows of cells."""
    parser = TableParser()
    parser.feed(html)
    return parser.rows


# ============================================================
# Pre-processor: clean OCR markdown before parsing
# ============================================================

def preprocess_markdown(md_text):
    """
    Clean and normalize OCR markdown output before section splitting.
    This is the key to improving rule-based accuracy.
    """
    text = md_text

    # 1. Remove image references: ![](page=0,bbox=[...])
    text = re.sub(r'!\[(?:[^\]]*)\]\([^)]*\)', '', text)

    # 2. Remove HTML div/align wrappers but keep content
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '', text, flags=re.IGNORECASE)

    # 3. Convert HTML tables to structured text (label: items format)
    def table_to_text(match):
        html = match.group(0)
        rows = parse_html_table(html)
        out = []
        for row in rows:
            if len(row) >= 2 and row[0] and row[1]:
                out.append(f"{row[0]}: {row[1]}")
            elif len(row) >= 1 and row[0]:
                out.append(row[0])
        return '\n'.join(out)

    text = re.sub(r'<table[^>]*>.*?</table>', table_to_text,
                  text, flags=re.DOTALL | re.IGNORECASE)

    # 4. Remove remaining stray HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # 5. Decode common HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")

    # 6. Merge standalone date lines with the heading above them
    #    OCR often puts "## Title, Company" and "Apr 2021 Present" on separate lines
    lines = text.split('\n')
    merged = []
    for line in lines:
        stripped = line.strip()
        if DATE_LINE_RE.match(stripped) and merged:
            prev = merged[-1].rstrip()
            merged[-1] = prev + ' | ' + stripped
        else:
            merged.append(line)
    text = '\n'.join(merged)

    # 7. Collapse 3+ blank lines into one
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 8. Strip trailing whitespace per line
    text = '\n'.join(line.rstrip() for line in text.split('\n'))

    return text.strip()


# ============================================================
# Helpers
# ============================================================

# Tokens that mean "still ongoing" or "future completion"
_PRESENT_TOKENS = {
    'present', 'current', 'ongoing', 'now', 'today',
    'in progress', 'in-progress',
}
_EXPECTED_TOKENS = {
    'expected', 'anticipated', 'projected', 'est', 'est.',
}


def _is_present_token(s):
    """Check if a string represents an ongoing / present-like end date."""
    return s.lower().strip() in _PRESENT_TOKENS


def _is_expected_prefix(s):
    """Check if a string is an expected/anticipated prefix."""
    return s.lower().strip().rstrip('.') in _EXPECTED_TOKENS


def normalize_date(raw):
    """Normalize 'Sept 2023' -> 'September 2023', 'present' -> 'Present'.

    Also handles:
      - 'Expected May 2026' -> 'Expected May 2026'
      - 'Anticipated 2027' -> 'Expected 2027'
      - 'In Progress' / 'Ongoing' / 'Current' -> 'Present'
    """
    if not raw:
        return None
    raw = raw.strip()

    # Direct present/current/ongoing tokens
    if _is_present_token(raw):
        return 'Present'

    # "Expected May 2026", "Anticipated 2027", "Est. Dec 2025"
    m = re.match(
        r'(?:expected|anticipated|projected|est\.?)\s+'
        r'((?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
        r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
        r'|Dec(?:ember)?)\s+)?\d{4})$',
        raw, re.IGNORECASE
    )
    if m:
        inner = normalize_date(m.group(1))  # normalise the date part
        return f"Expected {inner}"

    parts = raw.split()
    if len(parts) == 2:
        key = parts[0].lower().rstrip('.')
        if key in MONTH_MAP:
            return f"{MONTH_MAP[key]} {parts[1]}"
    if len(parts) == 1 and re.match(r'^\d{4}$', parts[0]):
        return raw
    return raw


def normalize_phone(raw):
    """Normalize phone to (XXX) XXX-XXXX."""
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 11 and digits[0] == '1':
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw


# Regex for present-like words anywhere in text
_PRESENT_RE = re.compile(
    r'\b(?:present|current|ongoing|now|in[- ]?progress)\b', re.IGNORECASE
)

# "Expected May 2026" style standalone phrases
_EXPECTED_DATE_RE = re.compile(
    r'(?:expected|anticipated|projected)\s+'
    r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
    r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?'
    r'|Dec(?:ember)?)\s+)?\d{4}',
    re.IGNORECASE
)


def extract_date_range(text):
    """Extract start_date and end_date from a text line.

    Handles normal ranges like 'Jan 2022 – May 2024' and also:
      - 'Jun 2025 – Present'
      - 'Aug 2023 – Expected May 2026'
      - 'Aug 2023 – In Progress'
      - 'Expected graduation: May 2026' (standalone)
    """
    m = DATE_RANGE_RE.search(text)
    if m:
        full = m.group(0)
        parts = re.split(r'\s*[-\u2013\u2014]\s*|\s+to\s+', full, maxsplit=1)
        if len(parts) == 2:
            return normalize_date(parts[0].strip()), normalize_date(parts[1].strip())

    m = YEAR_RANGE_RE.search(text)
    if m:
        return m.group(1), normalize_date(m.group(2))

    dates = SINGLE_DATE_RE.findall(text)
    has_present = bool(_PRESENT_RE.search(text))
    has_expected = _EXPECTED_DATE_RE.search(text)

    if len(dates) >= 2:
        return normalize_date(dates[0]), normalize_date(dates[1])
    if len(dates) == 1 and has_present:
        return normalize_date(dates[0]), 'Present'
    if len(dates) == 1 and has_expected:
        return None, "Expected " + normalize_date(dates[0])
    if len(dates) == 1:
        return normalize_date(dates[0]), None

    # Year-only fallback
    years = re.findall(r'\b((?:19|20)\d{2})\b', text)
    if len(years) >= 2:
        return years[0], years[-1]
    if len(years) == 1:
        if has_present:
            return years[0], 'Present'
        return years[0], None

    # Standalone present/in-progress with no start
    if has_present:
        return None, 'Present'

    return None, None


def _is_section_header(text):
    """Check if text matches any section header pattern."""
    stripped = text.strip()
    for pattern in SECTION_PATTERNS.values():
        if pattern.match(stripped):
            return True
    return False


# ============================================================
# Section splitting
# ============================================================

def split_sections(md_text):
    """Split markdown into named sections based on header patterns."""
    lines = md_text.split('\n')
    sections = {}
    current_section = "_header"
    current_lines = []

    for line in lines:
        matched = False
        stripped = line.strip()
        if not stripped and not current_lines:
            continue

        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(stripped):
                if current_lines:
                    if current_section in sections:
                        sections[current_section] += '\n' + '\n'.join(current_lines)
                    else:
                        sections[current_section] = '\n'.join(current_lines)
                current_section = section_name
                current_lines = []
                matched = True
                break

        if not matched:
            current_lines.append(line)

    if current_lines:
        if current_section in sections:
            sections[current_section] += '\n' + '\n'.join(current_lines)
        else:
            sections[current_section] = '\n'.join(current_lines)

    # Merge coursework into education
    if "coursework" in sections:
        if "education" in sections:
            sections["education"] += '\n## Relevant Coursework\n' + sections["coursework"]
        del sections["coursework"]

    return sections


# ============================================================
# Field extractors
# ============================================================

def extract_personal_info(header_text, full_text):
    """Extract contact info from header section and full text."""
    info = {
        "first_name": None, "last_name": None,
        "email": None, "phone": None,
        "address": None, "city": None, "state": None, "zip": None,
        "linkedin": None, "website": None,
    }

    # Email
    emails = EMAIL_RE.findall(header_text)
    if not emails:
        emails = EMAIL_RE.findall(full_text)
    if emails:
        info["email"] = emails[0]

    # Phone
    phones = PHONE_RE.findall(header_text)
    if not phones:
        phones = PHONE_RE.findall(full_text)
    if phones:
        info["phone"] = normalize_phone(phones[0])

    # LinkedIn
    linkedin = LINKEDIN_RE.search(full_text)
    if linkedin:
        url = linkedin.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        info["linkedin"] = url

    # GitHub / website
    github = GITHUB_RE.search(full_text)
    if github:
        url = github.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        info["website"] = url
    if not info["website"]:
        for url in URL_RE.findall(full_text):
            if 'linkedin.com' not in url.lower():
                info["website"] = url
                break

    # City, State
    city_state = CITY_STATE_RE.search(header_text)
    if not city_state:
        city_state = CITY_STATE_RE.search(full_text)
    if city_state:
        info["city"] = city_state.group(1).strip()
        state_raw = city_state.group(2).strip()
        if state_raw.upper() in STATE_ABBREVS:
            info["state"] = state_raw.upper()
        elif state_raw.lower() in STATE_NAMES:
            info["state"] = STATE_NAMES[state_raw.lower()]
        else:
            info["state"] = state_raw

    # ZIP
    zip_match = ADDRESS_ZIP_RE.search(header_text)
    if zip_match:
        info["zip"] = zip_match.group(1)

    # Name
    name = _extract_name(header_text, info)
    if name:
        parts = name.split(None, 1)
        info["first_name"] = parts[0] if parts else None
        info["last_name"] = parts[1] if len(parts) > 1 else None

    return info


def _extract_name(header_text, info):
    """Heuristic: the name is the first clean, prominent line in the header."""
    lines = header_text.strip().split('\n')

    skip_values = set()
    for v in [info.get("email"), info.get("phone"), info.get("linkedin"),
              info.get("website"), info.get("city"), info.get("zip")]:
        if v:
            skip_values.add(v.lower())

    for line in lines:
        cleaned = line.strip()
        cleaned = re.sub(r'^#{1,6}\s*', '', cleaned)
        cleaned = re.sub(r'\*\*?', '', cleaned)
        cleaned = cleaned.strip()
        if not cleaned:
            continue

        lower = cleaned.lower()

        # Skip OCR artifacts (image refs should be gone but just in case)
        if cleaned.startswith('![') or cleaned.startswith('<'):
            continue
        if any(sv in lower for sv in skip_values if sv):
            continue
        if EMAIL_RE.search(cleaned):
            continue
        if PHONE_RE.search(cleaned):
            continue
        if LINKEDIN_RE.search(cleaned):
            continue
        if URL_RE.search(cleaned):
            continue
        if ADDRESS_ZIP_RE.search(cleaned):
            continue
        if _is_section_header(cleaned):
            continue
        words = cleaned.split()
        if len(words) > 5:
            continue
        if not re.search(r'[a-zA-Z]', cleaned):
            continue
        if re.match(r'^[-=_|*\s]+$', cleaned):
            continue
        if CITY_STATE_RE.match(cleaned) and len(words) <= 3:
            continue
        if DATE_LINE_RE.match(cleaned):
            continue

        # Clean suffixes
        cleaned = re.sub(r'\s*,?\s*(?:Jr\.?|Sr\.?|III|II|IV|Ph\.?D\.?|M\.?D\.?)$', '', cleaned)
        cleaned = re.sub(r'\s*[|]\s*.*$', '', cleaned)
        result = cleaned.strip()
        if len(result) >= 2:
            return result

    # Fallback: infer from email
    email = info.get("email", "")
    if email:
        user = email.split('@')[0]
        parts = re.split(r'[._]', user)
        if len(parts) >= 2:
            name = ' '.join(p.capitalize() for p in parts[:2])
            if not re.search(r'\d', name):
                return name

    return None


# ============================================================
# Education parser — smart multi-line grouping
# ============================================================

INST_KEYWORDS_RE = re.compile(
    r'\b(?:university|college|school|institute|academy|polytechnic)\b',
    re.IGNORECASE
)

# Patterns that look like institution keywords but are actually degree names
DEGREE_WITH_SCHOOL_RE = re.compile(
    r'\bhigh\s+school\s+diploma\b', re.IGNORECASE
)

# Course code pattern: "ENGL 1010: ..." or "COMP 1990: ..."
COURSE_CODE_RE = re.compile(r'^[A-Z]{2,4}\s+\d{3,4}', re.IGNORECASE)


def _has_institution(text):
    """Check if text contains an institution keyword (not a degree with 'school')."""
    # Remove degree phrases that contain 'school' to avoid false positives
    cleaned = DEGREE_WITH_SCHOOL_RE.sub('', text)
    # Remove course code lines like "ENGL 1010: College Composition I"
    cleaned = COURSE_CODE_RE.sub('', cleaned)
    return bool(INST_KEYWORDS_RE.search(cleaned))


def extract_education(section_text):
    """Parse education entries with intelligent multi-line grouping.

    A new entry starts when we see:
      - A line with a full degree name AND the current entry already has one
      - A line with an institution keyword AND the current entry already has one
    Everything else merges into the current entry.
    """
    if not section_text:
        return []

    lines = section_text.strip().split('\n')

    # First pass: group into blocks by ## headers or blank lines
    blocks = []
    current_block = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('##') or stripped.startswith('**'):
            if current_block:
                blocks.append(current_block)
            header_text = re.sub(r'^#{1,4}\s*', '', stripped).strip()
            header_text = re.sub(r'\*\*?', '', header_text).strip()
            if header_text:
                current_block = [header_text]
            else:
                current_block = []
        elif not stripped:
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            clean = re.sub(r'^[-*\u2022]\s*', '', stripped)
            current_block.append(clean)

    if current_block:
        blocks.append(current_block)

    # Second pass: merge blocks into entries
    entries = []
    current_entry_lines = []

    # Pattern for coursework/skills sub-headers within education
    COURSEWORK_HEADER_RE = re.compile(
        r'(?:relevant\s+coursework|coursework|courses|skills)',
        re.IGNORECASE
    )

    for block in blocks:
        all_text = ' '.join(block)

        # Skip blocks that are just coursework headers or course listings
        # (These belong to the previous entry)
        is_coursework = bool(COURSEWORK_HEADER_RE.search(block[0]) if block else False)
        is_course_listing = all(COURSE_CODE_RE.match(line.strip()) for line in block if line.strip())

        if (is_coursework or is_course_listing) and current_entry_lines:
            current_entry_lines.extend(block)
            continue

        has_degree = _has_degree(all_text)
        has_inst = _has_institution(all_text)

        is_new = False
        if current_entry_lines:
            cur_text = ' '.join(current_entry_lines)
            cur_has_degree = _has_degree(cur_text)
            cur_has_inst = _has_institution(cur_text)

            if has_degree and cur_has_degree:
                is_new = True
            elif has_inst and cur_has_inst:
                is_new = True
        else:
            is_new = True  # Nothing yet, start new entry

        if is_new and current_entry_lines:
            entries.append(current_entry_lines[:])
            current_entry_lines = block[:]
        elif is_new:
            current_entry_lines = block[:]
        else:
            current_entry_lines.extend(block)

    if current_entry_lines:
        entries.append(current_entry_lines)

    # If we got one huge block, try splitting on degree keywords
    if len(entries) == 1 and len(entries[0]) > 6:
        entries = _split_large_edu_block(entries[0])

    return [_finalize_education(e) for e in entries]


def _split_large_edu_block(lines):
    """Split one large education blob on degree boundaries."""
    entries = []
    current = []
    for line in lines:
        if _has_degree(line) and current:
            cur_text = ' '.join(current)
            if _has_degree(cur_text):
                entries.append(current[:])
                current = [line]
                continue
        current.append(line)
    if current:
        entries.append(current)
    return entries if entries else [lines]


def _finalize_education(lines):
    """Convert grouped education lines into a structured entry."""
    all_text = ' '.join(lines)

    edu = {
        "institution": None, "degree": None, "field_of_study": None,
        "gpa": None, "start_date": None, "end_date": None, "is_current": False,
        "honors": [], "relevant_coursework": [],
    }

    # Degree
    edu["degree"] = _extract_degree(all_text)

    # Field of study: "in <field>" after degree, or "major" keyword
    if edu["degree"]:
        # Search only the line containing the degree, not all_text
        degree_line = None
        for line in lines:
            if edu["degree"] in line or DEGREE_FULL_RE.search(line):
                degree_line = line
                break
        if degree_line:
            fos = re.search(
                re.escape(edu["degree"]) + r'\s+in\s+(.+?)(?:\s*[,(|]|\s*$)',
                degree_line, re.IGNORECASE
            )
            if fos:
                val = fos.group(1).strip().rstrip(',.:;()')
                if len(val) > 2:
                    edu["field_of_study"] = val

    if not edu["field_of_study"]:
        fos = re.search(
            r'(?:major(?:ing)?(?:\s+in)?|concentration(?:\s+in)?|field\s+of\s+study)\s*:?\s*(.+?)(?:\s*[,|(]|\s*$)',
            all_text, re.IGNORECASE
        )
        if fos:
            val = fos.group(1).strip().rstrip(',.:;')
            if len(val) > 2 and not _has_institution(val):
                edu["field_of_study"] = val

    # GPA
    gpa_match = GPA_RE.search(all_text)
    if gpa_match:
        edu["gpa"] = f"{gpa_match.group(1)}/{gpa_match.group(2) or '4.00'}"
    else:
        gpa_match = GPA_STANDALONE_RE.search(all_text)
        if gpa_match:
            edu["gpa"] = f"{gpa_match.group(1)}/{gpa_match.group(2)}"

    # Dates
    start, end = extract_date_range(all_text)
    edu["start_date"] = start
    edu["end_date"] = end

    # In-progress / pursuing / candidate detection:
    # If we have a start date but no end date, and the text suggests
    # the education is ongoing, set end_date = 'Present'
    if edu["start_date"] and not edu["end_date"]:
        if re.search(
            r'\b(?:in[- ]?progress|pursuing|candidate|currently|current\s+student'
            r'|enrolled|expected|anticipated|ongoing|present)\b',
            all_text, re.IGNORECASE
        ):
            edu["end_date"] = 'Present'

    # Set is_current based on end_date
    if edu["end_date"] and isinstance(edu["end_date"], str):
        if edu["end_date"].lower() in ('present', 'current', 'ongoing', 'now', 'in progress', 'in-progress'):
            edu["is_current"] = True

    # Institution: line with university/college/school keyword
    for line in lines:
        clean = re.sub(r'\*\*?|^#{1,4}\s*', '', line).strip()
        if _has_institution(clean):
            inst = clean
            if edu["degree"]:
                inst = inst.replace(edu["degree"], '')
            inst = GPA_RE.sub('', inst)
            inst = GPA_STANDALONE_RE.sub('', inst)
            inst = DATE_RANGE_RE.sub('', inst)
            inst = YEAR_RANGE_RE.sub('', inst)
            inst = SINGLE_DATE_RE.sub('', inst)
            inst = re.sub(r'\([^)]*\)', '', inst)
            inst = re.sub(r'[|,\-\u2013\u2014]+\s*$', '', inst).strip()
            inst = re.sub(r'^\s*[|,\-\u2013\u2014]+', '', inst).strip()
            if inst and len(inst) > 3:
                edu["institution"] = inst
                break

    # Fallback institution: first line that doesn't look like a degree
    if not edu["institution"]:
        for line in lines:
            clean = re.sub(r'\*\*?|#{1,4}\s*', '', line).strip()
            if clean and not _has_degree(clean) and not GPA_RE.search(clean):
                clean = DATE_RANGE_RE.sub('', clean)
                clean = YEAR_RANGE_RE.sub('', clean)
                clean = re.sub(r'[|,\-\u2013\u2014]+\s*$', '', clean).strip()
                if clean and len(clean) > 3:
                    edu["institution"] = clean
                    break

    # Coursework
    in_cw = False
    for line in lines:
        lower = line.lower()
        if re.search(r'(?:course\s*work|relevant\s*course|courses)', lower):
            in_cw = True
            after = re.split(r':\s*', line, maxsplit=1)
            if len(after) > 1:
                courses = [c.strip() for c in re.split(r'[,;]', after[1]) if c.strip()]
                edu["relevant_coursework"].extend(courses)
        elif in_cw and line.strip().startswith('-'):
            course = line.strip().lstrip('-').strip()
            if course:
                edu["relevant_coursework"].append(course)
        elif in_cw and line.strip():
            courses = [c.strip() for c in re.split(r'[,;]', line.strip()) if c.strip()]
            edu["relevant_coursework"].extend(courses)
        elif in_cw and not line.strip():
            in_cw = False

    # Honors
    honor_keywords = ['cum laude', 'magna', 'summa', 'honors', 'dean',
                      'distinction', 'commonwealth', 'valedictorian', 'salutatorian']
    for line in lines:
        lower = line.lower()
        for kw in honor_keywords:
            if kw in lower:
                honor_text = re.sub(r'\*\*?|#{1,4}\s*', '', line).strip()
                if honor_text and honor_text not in edu["honors"]:
                    edu["honors"].append(honor_text)

    # Activities (often embedded in education section)
    edu["activities"] = []
    for line in lines:
        lower = line.strip().lower()
        if lower.startswith('activit') or lower.startswith('clubs') or lower.startswith('organizations'):
            after = re.split(r':\s*', line.strip(), maxsplit=1)
            if len(after) > 1:
                acts = [a.strip() for a in re.split(r'[,;]', after[1]) if a.strip()]
                edu["activities"].extend(acts)

    return edu


# ============================================================
# Work Experience parser
# ============================================================

def extract_work_experience(section_text):
    """Parse work experience entries.

    OCR typically outputs:
      ## Title, Company, City | Date Range
      - bullet 1
      - bullet 2
    """
    if not section_text:
        return []

    entries = []
    lines = section_text.strip().split('\n')
    current_entry = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_header = stripped.startswith('##') or stripped.startswith('**')
        is_bullet = stripped.startswith(('-', '*', '\u2022')) and not stripped.startswith('**')
        has_dates = bool(DATE_RANGE_RE.search(stripped) or YEAR_RANGE_RE.search(stripped)
                         or SINGLE_DATE_RE.search(stripped))

        if is_header:
            if current_entry:
                entries.append(_finalize_experience(current_entry))
            clean = re.sub(r'^#{1,4}\s*', '', stripped).strip()
            clean = re.sub(r'\*\*?', '', clean).strip()
            current_entry = {"header_lines": [clean], "bullets": []}
        elif has_dates and not is_bullet:
            # If the current entry already has bullets, this line with dates
            # is likely a NEW entry header, not a continuation.
            if current_entry and current_entry["bullets"]:
                entries.append(_finalize_experience(current_entry))
                current_entry = {"header_lines": [stripped], "bullets": []}
            elif current_entry:
                current_entry["header_lines"].append(stripped)
            else:
                current_entry = {"header_lines": [stripped], "bullets": []}
        elif is_bullet and current_entry:
            bullet_text = re.sub(r'^[-*\u2022]\s*', '', stripped)
            if bullet_text:
                current_entry["bullets"].append(bullet_text)
        elif current_entry:
            if current_entry["bullets"]:
                current_entry["bullets"][-1] += ' ' + stripped
            else:
                current_entry["header_lines"].append(stripped)
        else:
            current_entry = {"header_lines": [stripped], "bullets": []}

    if current_entry:
        entries.append(_finalize_experience(current_entry))

    return entries


def _finalize_experience(entry_data):
    """Convert raw experience data into structured entry."""
    header = ' | '.join(entry_data["header_lines"])
    header_clean = re.sub(r'\*\*?|#{1,4}\s*', '', header)

    exp = {
        "company": None, "title": None, "location": None,
        "start_date": None, "end_date": None, "is_current": False,
        "bullets": entry_data["bullets"],
    }

    # Dates
    start, end = extract_date_range(header)
    exp["start_date"] = start
    exp["end_date"] = end
    if end and isinstance(end, str) and end.lower() in ('present', 'ongoing', 'now', 'in progress', 'in-progress'):
        exp["is_current"] = True

    # If start but no end, check header/bullets for present-tense cues
    if exp["start_date"] and not exp["end_date"]:
        combined = header + ' ' + ' '.join(entry_data.get("bullets", []))
        if re.search(
            r'\b(?:present|current(?:ly)?|ongoing|now|to\s+date|still)\b',
            combined, re.IGNORECASE
        ):
            exp["end_date"] = 'Present'
            exp["is_current"] = True

    # Remove dates from header for company/title parsing
    cleaned = DATE_RANGE_RE.sub('', header_clean)
    cleaned = YEAR_RANGE_RE.sub('', cleaned)
    cleaned = SINGLE_DATE_RE.sub('', cleaned)
    cleaned = re.sub(r'\bPresent\b', '', cleaned, flags=re.IGNORECASE)

    # Location
    loc_match = CITY_STATE_RE.search(cleaned)
    if loc_match:
        exp["location"] = loc_match.group(0).strip()
        cleaned = cleaned.replace(loc_match.group(0), '')

    # Fallback location: if 3+ comma-separated parts, last short one may be a city
    if not exp["location"]:
        parts = [p.strip(' |') for p in cleaned.split(',') if p.strip(' |')]
        if len(parts) >= 3:
            candidate = parts[-1].strip(' |')
            if len(candidate.split()) <= 2 and len(candidate) > 1:
                exp["location"] = candidate
                cleaned = ','.join(parts[:-1])

    # Clean separators
    cleaned = re.sub(r'[|]+', ',', cleaned)
    cleaned = re.sub(r'\s*,\s*,\s*', ', ', cleaned)
    cleaned = cleaned.strip(' ,|-\u2013\u2014')

    # Split title / company by comma
    parts = [p.strip() for p in cleaned.split(',') if p.strip()]

    title_words = {'intern', 'assistant', 'associate', 'manager', 'director',
                   'engineer', 'developer', 'analyst', 'specialist', 'coordinator',
                   'consultant', 'supervisor', 'technician', 'officer', 'representative',
                   'clerk', 'counselor', 'advisor', 'resident', 'volunteer',
                   'cashier', 'server', 'tutor', 'barista', 'attendant',
                   'worker', 'aide', 'receptionist', 'operator', 'lead',
                   'customer', 'service', 'fulfillment', 'sales', 'support',
                   'researcher', 'architect', 'designer', 'administrator',
                   'trainer', 'driver', 'handler', 'chef', 'cook'}

    if len(parts) >= 2:
        p0_lower = parts[0].lower()
        p1_lower = parts[1].lower()
        p0_has_title = any(tw in p0_lower for tw in title_words)
        p1_has_title = any(tw in p1_lower for tw in title_words)

        if p0_has_title and not p1_has_title:
            exp["title"] = parts[0]
            exp["company"] = ', '.join(parts[1:])
        elif p1_has_title and not p0_has_title:
            exp["company"] = parts[0]
            exp["title"] = parts[1]
        elif parts[1].isupper():
            exp["title"] = parts[0]
            exp["company"] = parts[1]
        else:
            exp["title"] = parts[0]
            exp["company"] = ', '.join(parts[1:])
    elif len(parts) == 1:
        exp["title"] = parts[0]

    # If no company found but title is very long, it might contain both
    if not exp["company"] and exp["title"] and len(exp["title"].split()) > 4:
        # Try splitting on common separators within the title
        for sep in [' - ', ' at ', ' @ ']:
            if sep in exp["title"]:
                sub = exp["title"].split(sep, 1)
                exp["title"] = sub[0].strip()
                exp["company"] = sub[1].strip()
                break

    # If still no company, first word might be company name
    if not exp["company"] and exp["title"] and len(exp["title"].split()) > 2:
        words = exp["title"].split()
        first_lower = words[0].lower()
        has_title_word = any(tw in exp["title"].lower() for tw in title_words)
        if has_title_word and first_lower not in title_words:
            # first word is likely company, rest is title
            # find where the title-ish part starts
            for i, w in enumerate(words):
                if w.lower() in title_words or any(tw in w.lower() for tw in title_words):
                    exp["company"] = ' '.join(words[:i])
                    exp["title"] = ' '.join(words[i:])
                    break

    # Clean up
    for field in ["company", "title"]:
        if exp[field]:
            exp[field] = exp[field].strip(' ,|-\u2013\u2014')
            if exp["location"] and exp[field].endswith(exp["location"]):
                exp[field] = exp[field][:-(len(exp["location"]))].strip(' ,')

    return exp


# ============================================================
# Skills parser
# ============================================================

def extract_skills(section_text):
    """Parse skills into categories (technical, languages, tools, soft_skills)."""
    skills = {"technical": [], "languages": [], "tools": [], "soft_skills": []}
    if not section_text:
        return skills

    spoken_langs = {'english', 'spanish', 'french', 'german', 'chinese', 'mandarin',
                    'cantonese', 'japanese', 'korean', 'arabic', 'hindi', 'portuguese',
                    'russian', 'italian', 'vietnamese', 'tagalog', 'turkish', 'polish',
                    'dutch', 'greek', 'hebrew', 'swahili', 'urdu', 'bengali', 'thai',
                    'haitian creole', 'creole', 'cape verdean', 'khmer', 'cambodian'}

    tool_kws = {'microsoft', 'excel', 'word', 'powerpoint', 'outlook', 'office',
                'google', 'sheets', 'docs', 'slides', 'salesforce', 'tableau',
                'jira', 'trello', 'slack', 'zoom', 'teams', 'adobe', 'photoshop',
                'illustrator', 'figma', 'sketch', 'autocad', 'solidworks',
                'blender', 'unity', 'unreal', 'vscode', 'visual studio',
                'intellij', 'eclipse', 'jupyter', 'matlab', 'spss', 'sas',
                'quickbooks', 'sap', 'oracle', 'epic', 'cerner'}

    soft_kws = {'communication', 'leadership', 'teamwork', 'problem solving',
                'problem-solving', 'critical thinking', 'time management',
                'organization', 'interpersonal', 'collaboration', 'adaptability',
                'flexibility', 'creativity', 'attention to detail', 'detail-oriented',
                'customer service', 'public speaking', 'presentation', 'negotiation',
                'conflict resolution', 'decision making', 'multitasking',
                'self-motivated', 'analytical', 'research', 'mentoring',
                'project management', 'work ethic', 'reliability', 'patience',
                'empathy', 'resilience', 'discipline'}

    all_items = []

    prog_langs = {'python', 'java', 'javascript', 'c', 'c++', 'c#', 'go', 'rust',
                  'ruby', 'php', 'swift', 'kotlin', 'typescript', 'sql', 'html',
                  'css', 'r', 'scala', 'perl', 'bash', 'shell', 'matlab',
                  'assembly', 'dart', 'lua', 'haskell', 'elixir', 'clojure'}

    def _split_respecting_parens(text):
        """Split by commas/semicolons but keep parenthesized groups intact."""
        items = []
        depth = 0
        current = []
        for ch in text:
            if ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
                depth = max(0, depth - 1)
                current.append(ch)
            elif ch in ',;' and depth == 0:
                items.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            items.append(''.join(current).strip())
        return [i for i in items if i]

    def _classify_label(label, items):
        if any(k in label for k in ['technical', 'programming', 'software', 'computer',
                                     'technology', 'systems', 'hardware', 'networking',
                                     'administration', 'services', 'web', 'concept',
                                     'framework', 'methodolog']):
            skills["technical"].extend(items)
        elif any(k in label for k in ['spoken', 'foreign']):
            skills["languages"].extend(items)
        elif 'language' in label:
            is_prog = any(i.lower().split('(')[0].split('/')[0].strip() in prog_langs for i in items[:3])
            if is_prog:
                skills["technical"].extend(items)
            else:
                skills["languages"].extend(items)
        elif any(k in label for k in ['tool', 'platform', 'application', 'developer tool']):
            skills["tools"].extend(items)
        elif any(k in label for k in ['soft', 'interpersonal', 'transferable']):
            skills["soft_skills"].extend(items)
        else:
            all_items.extend(items)

    for line in section_text.strip().split('\n'):
        stripped = line.strip().strip('-*\u2022').strip()
        if not stripped or _is_section_header(stripped):
            continue

        # split lines that have multiple "Label: items. Label2: items" patterns
        sub_segments = re.split(r'\.?\s+(?=[A-Z][a-zA-Z\s]*:)', stripped)
        for seg in sub_segments:
            seg = seg.strip().rstrip('.')
            if not seg:
                continue
            label_m = re.match(r'^([^:]+):\s*(.+)$', seg)
            if label_m:
                label = label_m.group(1).strip().lower()
                items = _split_respecting_parens(label_m.group(2))
                items = [i.rstrip('.') for i in items if i.rstrip('.')]
                _classify_label(label, items)
            else:
                items = _split_respecting_parens(seg)
                all_items.extend(items)

    # Auto-categorize uncategorized items
    for item in all_items:
        lower = item.lower().strip()
        if not lower:
            continue
        if lower in spoken_langs or any(lang in lower for lang in spoken_langs):
            skills["languages"].append(item)
        elif lower in soft_kws or any(sk in lower for sk in soft_kws):
            skills["soft_skills"].append(item)
        elif any(tk in lower for tk in tool_kws):
            skills["tools"].append(item)
        else:
            skills["technical"].append(item)

    # Deduplicate
    for cat in skills:
        seen = set()
        deduped = []
        for item in skills[cat]:
            key = item.lower().strip()
            if key not in seen and key:
                seen.add(key)
                deduped.append(item)
        skills[cat] = deduped

    return skills


def extract_simple_list(section_text):
    """Extract a flat list of items from a section."""
    if not section_text:
        return []
    items = []
    for line in section_text.strip().split('\n'):
        stripped = line.strip().strip('-*\u2022').strip()
        if not stripped or _is_section_header(stripped):
            continue
        cleaned = re.sub(r'\*\*?|^#{1,4}\s*', '', stripped).strip()
        if cleaned:
            items.append(cleaned)
    return items


def extract_projects(section_text):
    """Parse project entries."""
    if not section_text:
        return []
    entries = []
    lines = section_text.strip().split('\n')
    current = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_bullet = stripped.startswith(('-', '*', '\u2022')) and not stripped.startswith('**')
        is_header = stripped.startswith('##') or stripped.startswith('**')

        # detect pipe-separated project headers like "ProjectName | Tech1, Tech2"
        if not is_header and not is_bullet and '|' in stripped:
            pipe_parts = [p.strip() for p in stripped.split('|', 1)]
            if len(pipe_parts) == 2 and len(pipe_parts[0].split()) <= 6:
                is_header = True
                stripped = stripped  # keep as-is, handle below

        if is_header:
            if current:
                entries.append(current)
            name = re.sub(r'\*\*?|#{1,4}\s*', '', stripped).strip()

            techs = []
            # pipe-separated techs: "Name | Tech1, Tech2, Tech3"
            if '|' in name:
                pipe_parts = [p.strip() for p in name.split('|', 1)]
                name = pipe_parts[0].strip()
                techs = [t.strip() for t in pipe_parts[1].split(',') if t.strip()]

            # parenthesized techs: "Name (Tech1, Tech2)"
            if not techs:
                tech_match = re.search(r'\(([^)]+)\)', name)
                if tech_match:
                    techs = [t.strip() for t in tech_match.group(1).split(',')]
                    name = name.replace(tech_match.group(0), '').strip()

            start, end = extract_date_range(name)
            date_str = None
            if start:
                date_str = f"{start}" + (f" - {end}" if end else "")
                name = DATE_RANGE_RE.sub('', name)
                name = YEAR_RANGE_RE.sub('', name)
                name = name.strip(' |-\u2013')
            current = {
                "name": name or None, "description": None,
                "technologies": techs, "url": None, "date": date_str,
                "_bullets": [],
            }
        elif is_bullet and current:
            text = re.sub(r'^[-*\u2022]\s*', '', stripped)
            current["_bullets"].append(text)
            url = URL_RE.search(text)
            if url and not current["url"]:
                current["url"] = url.group(0)
        elif current:
            if not current["date"]:
                s, e = extract_date_range(stripped)
                if s or e:
                    date_str = f"{s}" + (f" - {e}" if e else "") if s else e
                    current["date"] = date_str
                    continue
            current["_bullets"].append(stripped)

    if current:
        entries.append(current)

    for proj in entries:
        bullets = proj.pop("_bullets", [])
        proj["bullets"] = bullets
        if bullets:
            proj["description"] = ' '.join(bullets)

    return entries


def extract_certifications(section_text):
    """Parse certification entries."""
    if not section_text:
        return []
    certs = []
    for line in section_text.strip().split('\n'):
        stripped = line.strip().strip('-*\u2022').strip()
        if not stripped or _is_section_header(stripped):
            continue
        cleaned = re.sub(r'\*\*?|^#{1,4}\s*', '', stripped).strip()
        if not cleaned:
            continue
        cert = {"name": None, "issuer": None, "date": None}
        start, end = extract_date_range(cleaned)
        dates = SINGLE_DATE_RE.findall(cleaned)
        years = re.findall(r'\b((?:19|20)\d{2})\b', cleaned)
        if start:
            cert["date"] = normalize_date(str(start))
            cleaned = DATE_RANGE_RE.sub('', cleaned)
            cleaned = YEAR_RANGE_RE.sub('', cleaned)
        elif dates:
            cert["date"] = normalize_date(dates[0])
            cleaned = SINGLE_DATE_RE.sub('', cleaned)
        elif years:
            cert["date"] = years[0]
        cleaned = cleaned.strip(' ,|-\u2013\u2014')
        parts = re.split(r'\s*[-\u2013\u2014,]\s*', cleaned)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            cert["name"] = parts[0]
            cert["issuer"] = parts[1]
        elif parts:
            cert["name"] = parts[0]
        if cert["name"]:
            certs.append(cert)
    return certs


# ============================================================
# Main parser
# ============================================================

def parse_resume_markdown(md_text):
    """
    Parse OCR-extracted markdown into structured resume JSON.
    Pure rule-based, no LLM, no external dependencies.
    """
    cleaned_md = preprocess_markdown(md_text)
    sections = split_sections(cleaned_md)

    header_text = sections.get("_header", "")

    personal_info = extract_personal_info(header_text, cleaned_md)
    summary = None
    if "summary" in sections:
        raw = re.sub(r'\*\*?|^#{1,4}\s*', '', sections["summary"].strip()).strip()
        if raw:
            summary = raw

    education = extract_education(sections.get("education", ""))

    # Infer city/state from first education institution if not in header
    if not personal_info.get("city") and education:
        for edu in education:
            inst = edu.get("institution", "") or ""
            cs = CITY_STATE_RE.search(inst)
            if cs:
                personal_info["city"] = cs.group(1).strip()
                state_raw = cs.group(2).strip()
                personal_info["state"] = state_raw.upper() if state_raw.upper() in STATE_ABBREVS else state_raw
                break

    work_experience = extract_work_experience(sections.get("work_experience", ""))

    skills_text = sections.get("skills", "")
    # pull certifications/awards lines out of skills section if mixed
    extra_certs = []
    extra_activities = []
    filtered_skills_lines = []
    for line in skills_text.split('\n'):
        lower = line.strip().lower()
        if lower.startswith('certification') or lower.startswith('licenses'):
            after = re.split(r':\s*', line.strip(), maxsplit=1)
            if len(after) > 1:
                extra_certs.extend([c.strip() for c in re.split(r'[,;]', after[1]) if c.strip()])
            else:
                filtered_skills_lines.append(line)
        elif lower.startswith('award'):
            filtered_skills_lines.append(line)
        else:
            filtered_skills_lines.append(line)
    skills = extract_skills('\n'.join(filtered_skills_lines))

    projects = extract_projects(sections.get("projects", ""))
    certifications = extract_certifications(sections.get("certifications", ""))
    certifications.extend(extra_certs)
    awards = extract_simple_list(sections.get("awards", ""))
    activities = extract_simple_list(sections.get("activities", ""))
    # merge activities found inside education entries
    for edu in education:
        edu_acts = edu.pop("activities", [])
        activities.extend(edu_acts)
    volunteer = extract_simple_list(sections.get("volunteer", ""))

    return {
        "personal_info": personal_info,
        "summary": summary,
        "education": education,
        "work_experience": work_experience,
        "skills": skills,
        "projects": projects,
        "certifications": certifications,
        "awards": awards,
        "activities": activities,
        "volunteer": volunteer,
    }


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        md_text = data.get("md_results", "")
        if not md_text:
            print("No md_results found.")
            sys.exit(1)
    else:
        md_text = sys.stdin.read()

    result = parse_resume_markdown(md_text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
