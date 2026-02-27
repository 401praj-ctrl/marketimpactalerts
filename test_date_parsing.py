import re

def parse_published_date(date_str):
    if not date_str: return None
    
    # Translate French date parts to English
    french_to_english = {
        'janv': 'Jan', 'févr': 'Feb', 'mars': 'Mar', 'avr': 'Apr',
        'mai': 'May', 'juin': 'Jun', 'juill': 'Jul', 'août': 'Aug',
        'sept': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'déc': 'Dec',
        'janvier': 'Jan', 'février': 'Feb', 'avril': 'Apr',
        'juillet': 'Jul', 'septembre': 'Sep', 'octobre': 'Oct',
        'novembre': 'Nov', 'décembre': 'Dec',
        'lun': 'Mon', 'mar': 'Tue', 'mer': 'Wed', 'jeu': 'Thu',
        'ven': 'Fri', 'sam': 'Sat', 'dim': 'Sun',
        'lundi': 'Mon', 'mardi': 'Tue', 'mercredi': 'Wed',
        'jeudi': 'Thu', 'vendredi': 'Fri', 'samedi': 'Sat',
        'dimanche': 'Sun'
    }
    
    clean_str = date_str
    for fr, en in french_to_english.items():
        # Match word boundaries or dots (for abbreviations like ven.)
        # We use a case-insensitive replacement
        pattern = re.compile(rf'\b{fr}\b\.?', re.IGNORECASE)
        clean_str = pattern.sub(en, clean_str)

    try:
        from dateutil import parser as d_parser
        dt = d_parser.parse(clean_str)
        return dt
    except Exception as e:
        print(f"FAILED to parse '{date_str}' (Clean: '{clean_str}'): {e}")
        return None

test_cases = [
    "ven., 27 févr. 2026 10:32:38 +0530",
    "lun., 23 janv. 2026 08:00:00 +0530",
    "Wed, 25 Feb 2026 19:36:36 +0530",
    "vendredi, 27 février 2026 10:32:38 +0530"
]

for tc in test_cases:
    res = parse_published_date(tc)
    if res:
        print(f"SUCCESS: '{tc}' -> {res}")
