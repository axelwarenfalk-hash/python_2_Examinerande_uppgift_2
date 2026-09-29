import pdfplumber
import re
import logging

logger = logging.getLogger(__name__)

def split_first_member(member: str) -> tuple[dict[str, str | None], str]:

    name, rest = member.strip().split("(", 1)
    name = name.strip()

    party, rest = rest.strip().split(")",1)
    party = party.strip()

    rest = rest.strip()

    if rest.startswith('('):
        title, rest = rest.split(')',1)
        title = title.replace('(', '')
    else:
        title = None

    structured_member = {
        'name': name,
        'party': party,
        'title': title
    }

    return structured_member, rest.strip()

def paragraph_interval(paragraph: str) -> list[int] | None:
    '''
    Tar en eller flera paragrafintevall i en sträng och returnerar en lista med paragraferna.
    ex:
    '§§56-59, §§62-65' --> [56, 57, 58, 59, 62, 63, 65]
    '''

    if '§' not in paragraph:
        return None

    paragraph = paragraph.replace('–', '-')
    # Närvaro under delpunkter räknas som närvaro under hela paragrafen.
    paragraph = re.sub(r"\(\s*p\.?\s*\d[\d\s,\-]*\)", "", paragraph, flags=re.IGNORECASE)
    paragraph = paragraph.replace('§', '').strip()
    paragraphs = paragraph.split(',')

    expanded = []

    for part in paragraphs:
        part = part.strip()

        if '-' in part:
            start, end = map(int, part.split('-'))
            expanded.extend(range(start, end + 1))
        else:
            expanded.append(int(part))

    return expanded


def get_text_from_pdf(pdf_path) -> list[str] | None:
    logger.info('extraherar text från pdf')
    all_lines = []
    attendance_finished = False
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Grafik utan läsbara bokstäver kan vara text ritad som konturer.
            if not attendance_finished and not any(char.isalpha() for char in text):
                if page.curves or page.images:
                    logger.warning(
                        "Hoppar över %s: sida %d har grafik men saknar läsbar text",
                        pdf_path, page.page_number,
                    )
                    return None
            all_lines.extend(text.splitlines())
            if "ej tjänstgörande ersättare" in text.lower():
                attendance_finished = True

    return all_lines


def get_meeting_paragraphs(all_lines):
    logger.info('Hämtar mötets paragrafer')
    for line in all_lines:
        lower = line.lower()
        if 'protokollet omfattar' in lower:
            meeting_paragraphs = line.split('omfattar', 1)[1].strip()
            meeting_paragraphs = paragraph_interval(meeting_paragraphs)

            return meeting_paragraphs
        
    return []

def get_attendance_sections(all_lines):
    logger.info('Hämtar mötets närvarolista')
    # Ta ut alla ledamöter
    voting_members = []
    voting_member_section = False

    for line in all_lines:
        lower = line.lower()

        if lower.strip().isdigit():
            continue

        if "beslutande ledamöter" in lower:
            voting_member_section = True
            continue

        if "ersätter" in lower:
            break

        if voting_member_section:
            voting_members.append(line)


    # Ta ut alla replacements
    voting_replacements = []
    voting_member_section = False

    for line in all_lines:
        lower = line.lower()

        if lower.strip().isdigit():
            continue
        
        if voting_members[-1].lower() in lower:
            voting_member_section = True
            continue

        if "ej tjänstgörande ersättare" in lower:
            break

        if voting_member_section:
            voting_replacements.append(line)

    return voting_members, voting_replacements


def structure_members_section(members_section, meeting_paragraphs):
    
    voting_members_dicts = []

    for member_row in members_section:

        structured_member, rest = split_first_member(member_row)
        paragraph = paragraph_interval(rest)

        if paragraph == None:
            paragraph = meeting_paragraphs

        voting_members_dicts.append(
            {
                'name': structured_member['name'],
                'party': structured_member['party'],
                'paragraphs': paragraph
            }
        )

    return voting_members_dicts


def get_right_syntax_replacements(replacements_section):

    voting_replacements_merged = []
    extra_row_number = -1

    for i, replacement_row in enumerate(replacements_section):

        if extra_row_number == i:
            continue

        replacement_row = replacement_row.strip()

        # Tillåt både § och §§, med eller utan mellanslag före numret.
        correct_syntax = (
            r"^§{1,2}\s*\d{1,3}(?:-\d{1,3})?"
            r"(?:,\s*§{1,2}\s*\d{1,3}(?:-\d{1,3})?)*"
            r"\s+ersätter\s+.+?\s+\([A-Za-zÅÄÖåäö]+\)"
            r"(?:\s+\([^)]+\))?(?:\s+pga jäv)?\s*$"
        )

        comma_after_parantes = re.search(r"\)(?:\s+pga jäv)?\s*,", replacement_row)

        if comma_after_parantes:
            after_comma = replacement_row[comma_after_parantes.end():].strip()

            if re.match(correct_syntax, after_comma):
                voting_replacements_merged.append(replacement_row)
            else:
                if i + 1 >= len(replacements_section):
                    raise ValueError(
                        f"Ersättarraden kunde inte tolkas och saknar fortsättningsrad: {replacement_row}"
                    )
                merged = replacement_row + ' ' + replacements_section[i+1]
                voting_replacements_merged.append(merged)
                extra_row_number = i + 1

        else:
            voting_replacements_merged.append(replacement_row)

    return voting_replacements_merged


def structure_replacements_section(replacements_section, meeting_paragraphs):

    voting_extras_dict = []

    for replacement in replacements_section:
        replacement, rest = split_first_member(replacement)

        replacement['replaces'] = []

        # Delpunkter räknas som hela paragrafer och ska inte dela ersättningar.
        rest = re.sub(r"\(\s*p\.?\s*\d[\d\s,\-–]*\)", "", rest, flags=re.IGNORECASE)

        # Dela efter parti/titel eller jäv, men behåll komman mellan intervall.
        members = re.split(r"(?:(?<=\))|(?<=pga jäv))\s*,\s*", rest)

        for member in members:
            member = member.split('ersätter')

            paragraph = member[0].strip()
            paragraphs = paragraph_interval(paragraph)

            if paragraphs == None:
                paragraphs = meeting_paragraphs

            name = member[1].strip()
            name, rest = split_first_member(name)
            reason = "jäv" if "pga jäv" in rest.lower() else None

            replacement['replaces'].append(
                {
                    'member': name,
                    'paragraphs': paragraphs,
                    'reason': reason
                }
            )

        voting_extras_dict.append(replacement)

    return voting_extras_dict
