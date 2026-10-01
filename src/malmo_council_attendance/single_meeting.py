"""Läs ett mötesprotokoll och tolka paragrafer, ledamöter och ersättningar."""

from pathlib import Path
from typing import Any

import pdfplumber
from pdfplumber.page import Page
import re
import logging

from .io import read_json, save_json

logger = logging.getLogger(__name__)

def split_first_member(member: str) -> tuple[dict[str, str | None], str]:
    """Dela första personens namn, parti och eventuell titel från resten av raden."""

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
    '§§56-59, §§62-65' --> [56, 57, 58, 59, 62, 63, 64, 65]
    '''

    if '§' not in paragraph:
        return None

    paragraph = paragraph.replace('–', '-')
    # Närvaro under delpunkter räknas som närvaro under hela paragrafen.
    paragraph = re.sub(r"\(\s*(?:p\.?|beslutsgrupp)\s*\d[\d\s,\-]*\)", "", paragraph, flags=re.IGNORECASE)
    # Ett nytt paragraftecken efter ett nummer kan ersätta ett komma.
    paragraph = re.sub(r"(?<=\d)\s*(?=§)", ", ", paragraph)
    # Ett avslutande komma före "ersätter" hör inte till paragrafnumret.
    paragraph = paragraph.replace('§', '').strip(' ,')
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


def remove_page_number(page: Page) -> Page:
    """Filtrera bort sidans eget nummer i övre högra hörnet före textutvinning."""
    # Ta bara bort sidans eget nummer i det övre högra hörnet.
    for word in page.extract_words():
        if (
            word["text"] == str(page.page_number)
            and word["x0"] > page.width * 0.85
            and word["bottom"] < 65
        ):
            return page.filter(
                lambda obj: not (
                    obj["object_type"] == "char"
                    and word["x0"] <= obj["x0"] < word["x1"]
                    and word["top"] <= obj["top"] < word["bottom"]
                )
            )
    return page


def get_text_from_pdf(pdf_path: Path) -> list[str] | None:
    """Läs PDF-rader; returnera None om närvarodelen innehåller oläsbar grafik."""
    logger.info('extraherar text från pdf')
    all_lines = []
    attendance_finished = False
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = remove_page_number(page).extract_text() or ""
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


def get_meeting_paragraphs(all_lines: list[str]) -> list[int] | None:
    """Hämta paragrafnumren från raden som anger vad protokollet omfattar."""
    logger.info('Hämtar mötets paragrafer')
    for line in all_lines:
        lower = line.lower()
        if 'protokollet omfattar' in lower:
            meeting_paragraphs = line.split('omfattar', 1)[1].strip()
            meeting_paragraphs = paragraph_interval(meeting_paragraphs)

            return meeting_paragraphs
        
    return []

def get_attendance_lines(all_lines: list[str]) -> list[str]:
    """Hämta närvarodelen mellan dess rubriker; avbryt om slutrubriken saknas."""
    attendance_lines = []
    in_section = False

    for line in all_lines:
        line = line.strip()
        lower = line.lower()
        if "beslutande ledamöter" in lower:
            in_section = True
            continue
        if in_section and "ej tjänstgörande ersättare" in lower:
            return attendance_lines
        if in_section and line and not line.isdigit():
            attendance_lines.append(line)

    raise ValueError("Kunde inte hitta hela avsnittet för beslutande ledamöter")


def attendance_row_is_complete(row: str) -> bool:
    """Kontrollera om en personpost ser komplett ut innan nästa person börjar."""
    if "ersätter" in row.lower():
        # Den sista ersatta personen ska ha ett namn och en partibeteckning.
        last_member = re.split("ersätter", row, flags=re.IGNORECASE)[-1]
        last_member = re.sub(
            r"\(\s*(?:p\.?|beslutsgrupp)\s*\d[\d\s,\-–]*\)",
            "", last_member, flags=re.IGNORECASE,
        )
        return re.fullmatch(
            r"\s*[^()]+\([A-Za-zÅÄÖåäö-]+\)(?:\s*\([^)]*\))?(?:\s+pga jäv)?"
            r"(?:\s*§{1,2}\s*\d(?:[\d\s,§–-]*\d)?)?\s*",
            last_member,
            flags=re.IGNORECASE,
        ) is not None

    # En ledamotsrad får inte sluta mitt i en parentes eller ett intervall.
    return (
        row.count("(") == row.count(")")
        and re.search(r"[\d)]$", row) is not None
    )


def merge_attendance_lines(attendance_lines: list[str]) -> list[str]:
    """Slå ihop radbrutna personposter och rätta kända parentes- och kommafel."""
    person_rows = []
    current_row = ""
    person_start = r"^[^()\d§,]+\([A-Za-zÅÄÖåäö-]+\)"

    for line in attendance_lines:
        # Rätta en extra öppningsparentes runt partibeteckningen, t.ex. ((L).
        line = re.sub(r"\(\(([A-Za-zÅÄÖåäö-]+)\)", r"(\1)", line)
        # Kommat mellan ersättningar kan ha hamnat inuti partiets parentes.
        line = re.sub(r"\(([A-Za-zÅÄÖåäö-]+),\)", r"(\1),", line)
        starts_person = (
            re.match(person_start, line) is not None
            and not line.lower().startswith("ersätter")
        )
        if not current_row:
            current_row = line
        elif starts_person and attendance_row_is_complete(current_row):
            person_rows.append(current_row)
            current_row = line
        else:
            # Ett ersatt namn kan fortsätta med flera namnled innan partiet kommer.
            last_member = re.split("ersätter", current_row, flags=re.IGNORECASE)[-1]
            continues_name = (
                "ersätter" in current_row.lower()
                and "(" not in last_member
            )
            if starts_person and not continues_name:
                raise ValueError(f"Oklar radbrytning mellan: {current_row!r} och {line!r}")
            current_row += " " + line

    if current_row:
        if not attendance_row_is_complete(current_row):
            raise ValueError(f"Ofullständig personpost: {current_row}")
        person_rows.append(current_row)

    return person_rows


def get_attendance_sections(all_lines: list[str]) -> tuple[list[str], list[str]]:
    """Returnera sammanfogade ledamotsrader och ersättarrader var för sig."""
    logger.info("Hämtar mötets närvarolista")
    attendance_lines = get_attendance_lines(all_lines)
    person_rows = merge_attendance_lines(attendance_lines)
    members_section = []
    replacements_section = []

    for row in person_rows:
        if "ersätter" in row.lower():
            replacements_section.append(row)
        else:
            members_section.append(row)

    return members_section, replacements_section


def structure_members_section(
    members_section: list[str], meeting_paragraphs: list[int]
) -> list[dict[str, Any]]:
    """Koppla ledamöternas namn och parti till paragrafer; inga angivna betyder alla."""
    
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


def structure_replacements_section(
    replacements_section: list[str], meeting_paragraphs: list[int]
) -> list[dict[str, Any]]:
    """Tolka vem varje ersättare ersätter, under vilka paragrafer och eventuell jävorsak."""

    voting_extras_dict = []

    for replacement_row in replacements_section:
        person, rest = split_first_member(replacement_row)
        replacement: dict[str, Any] = dict(person)

        replacement['replaces'] = []

        # Delpunkter räknas som hela paragrafer och ska inte dela ersättningar.
        rest = re.sub(r"\(\s*(?:p\.?|beslutsgrupp)\s*\d[\d\s,\-–]*\)", "", rest, flags=re.IGNORECASE)

        # Dela efter parti/titel eller namn, men behåll komman mellan intervall.
        members = re.split(r"(?:(?<=\))|(?<=[A-Za-zÅÄÖåäö]))\s*,\s*", rest)

        for member in members:
            member = member.split('ersätter')

            paragraph = member[0].strip()
            paragraphs = paragraph_interval(paragraph)

            name = member[1].strip()
            if "(" in name:
                name, rest = split_first_member(name)
            else:
                # Partiet kan saknas i protokollet; gissa inte vilket det är.
                name = {"name": name, "party": None, "title": None}
                rest = ""
            reason = "jäv" if "pga jäv" in rest.lower() else None

            # I vissa protokoll står paragraferna efter den ersatta personen.
            if paragraphs is None:
                paragraphs = paragraph_interval(rest)
            if paragraphs is None:
                paragraphs = meeting_paragraphs

            replacement['replaces'].append(
                {
                    'member': name,
                    'paragraphs': paragraphs,
                    'reason': reason
                }
            )

        voting_extras_dict.append(replacement)

    return voting_extras_dict


def read_meeting(pdf_path: Path) -> dict[str, Any]:
    """Tolka ett protokoll och returnera lässtatus samt närvarodata om det lyckas."""
    pdf_text = get_text_from_pdf(pdf_path)
    if pdf_text is None:
        return {"status": "unreadable_text"}
    paragraphs = get_meeting_paragraphs(pdf_text)
    if not paragraphs:
        logger.warning("Inga paragrafer hittades för %s", pdf_path.name)
        return {"status": "missing_paragraphs"}
    members, replacements = get_attendance_sections(pdf_text)
    return {
        "status": "processed",
        "paragraphs": paragraphs,
        "members": structure_members_section(members, paragraphs),
        "replacements": structure_replacements_section(replacements, paragraphs),
    }


def load_meeting_reading(pdf_path: Path, cache_dir: Path, use_cache: bool = True) -> dict[str, Any]:
    """Återanvänd PDF-tolkning om filstorlek och ändringstid matchar, annars läs om."""
    if not pdf_path.exists():
        logger.info("%s finns inte", pdf_path.name)
        return {"status": "missing_pdf"}
    cache_path = cache_dir / f"{pdf_path.stem}.json"
    pdf_stat = pdf_path.stat()
    pdf_version = [pdf_stat.st_size, pdf_stat.st_mtime_ns]
    if use_cache and cache_path.exists():
        reading = read_json(cache_path)
        if reading["pdf_version"] == pdf_version:
            logger.info("Använder sparad PDF-tolkning för %s", pdf_path.name)
            return reading
    reading = read_meeting(pdf_path)
    reading["pdf_version"] = pdf_version
    save_json(reading, cache_path)
    return reading
