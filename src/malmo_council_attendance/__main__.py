# moduler
from .io import(
    get_api_json,
    get_page_html,
    download_pdf
)
from .config import(
    ReportConfig
)
from .config_logging import(
    config_logging
)
from .council import(
    make_all_representatives_dataframe,
    make_all_roles_dataframe,
    merge_all_representatives_with_all_roles,
    separate_members_from_replacements
)
from .meetings import(
    find_meeting_urls,
    find_pdf_url,
)
from .single_meeting import(
    get_text_from_pdf,
    get_attendance_sections,
    get_meeting_paragraphs,
    structure_members_section,
    get_right_syntax_replacements,
    structure_replacements_section
)

# Paket
import logging
from pathlib import Path
import pandas as pd
import pdfplumber
import re


refresh_cache = False

logger = logging.getLogger("malmo_council_attendance")

cache_path = Path("data/meeting_protocol_links.csv")

def main():
    config_logging()
    logger.info("Startar inläsning av kommunfullmäktiges grunddata")

    # Hämtar namn och parti på alla ledamöter och erssättare från malmöstads api
    all_representatives_json = get_api_json(ReportConfig.api_url_all_council_representatives)
    if not isinstance(all_representatives_json, dict):
        raise TypeError("Förväntade en ordbok med personuppgifter")
    all_representatives_df = make_all_representatives_dataframe(all_representatives_json)

    # Hämtar alla roller på ledamöter och erssättare från malmöstads andra api
    all_roles_json = get_api_json(ReportConfig.api_url_all_council_roles)
    if not isinstance(all_roles_json, list):
        raise TypeError("Förväntade en lista med roller")
    all_roles_df = make_all_roles_dataframe(all_roles_json)

    # Slår ihop både namn och roll df:erna
    all_representatives_with_roles_df = merge_all_representatives_with_all_roles(all_representatives_df, all_roles_df)

    # Separerar på ledamöter och ersättare till två olika dfs
    members_df, replacements_df = separate_members_from_replacements(all_representatives_with_roles_df)

    
    # Hämtar html från meetingssidan
    all_meetings_html = get_page_html(ReportConfig.url_all_meetings)
    # tar ut rätt länkar från hmtl och lägger i df hela länkadressen
    all_meetings_df = find_meeting_urls(all_meetings_html, ReportConfig.base_url)

    # gå igenom varje länk i all_meetings_df och hitta pdf-länk och spara i all_meetings_df
    if cache_path.exists() and not refresh_cache:
        all_meetings_df = pd.read_csv(cache_path, parse_dates=["date"])
    else: 
        pdf_urls = []
        for url in all_meetings_df['url']:
            html = get_page_html(url)
            pdf_url = find_pdf_url(html)
            pdf_urls.append(pdf_url)

        all_meetings_df["pdf_url"] = pdf_urls
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        all_meetings_df.to_csv(cache_path, index=False)


    # Laddar ner alla pdf:er
    for _, row in all_meetings_df.iterrows():
        download_pdf(row)


    attendance_rows = []
    all_meetings_df["read_status"] = "not_processed"
    all_meetings_df.to_csv(cache_path, index=False)

    # Kolla i all_meetings_df och öppnar sedan korresponderande nerladdad pdf.
    for index, meeting in all_meetings_df.iterrows():
        filename = meeting["date"].strftime("%Y-%m-%d") + ".pdf"
        pdf_path = Path("data/pdfs") / filename

        logger.info("Läser in %s", filename)

        if not pdf_path.exists():
            logger.info( "%s finns inte", filename)
            all_meetings_df.at[index, "read_status"] = "missing_pdf"
            all_meetings_df.to_csv(cache_path, index=False)
            continue

        pdf_text = get_text_from_pdf(pdf_path)
        if pdf_text is None:
            all_meetings_df.at[index, "read_status"] = "unreadable_text"
            all_meetings_df.to_csv(cache_path, index=False)
            continue

        meeting_paragraphs = get_meeting_paragraphs(pdf_text)
        if not meeting_paragraphs:
            logger.warning("Inga paragrafer hittades för %s", filename)
            all_meetings_df.at[index, "read_status"] = "missing_paragraphs"
            all_meetings_df.to_csv(cache_path, index=False)
            continue


        # Extrahera mötesinformation
        members_section, replacements_section = get_attendance_sections(pdf_text)
        members_attendance = structure_members_section(members_section, meeting_paragraphs)
        replacements_section_syntax = get_right_syntax_replacements(replacements_section)
        replacements_attendance = structure_replacements_section(replacements_section_syntax, meeting_paragraphs)


        # Skapa en rad per paragraf och ordinarie ledamot.
        for paragraph in meeting_paragraphs:
            for _, member in members_df.iterrows():
                status = "absent_without_replacement"
                replaced_by = None

                for attending_member in members_attendance:
                    if attending_member["name"] == member["name"]:
                        if paragraph in attending_member["paragraphs"]:
                            status = "present"
                            break

                if status != "present":
                    for replacement in replacements_attendance:
                        for replaced_member in replacement["replaces"]:
                            if replaced_member["member"]["name"] == member["name"]:
                                if paragraph in replaced_member["paragraphs"]:
                                    status = "absent_with_replacement"
                                    replaced_by = replacement["name"]
                                    break
                        if replaced_by is not None:
                            break

                attendance_rows.append({
                    "date": meeting["date"],
                    "paragraph": paragraph,
                    "representative_id": member["representative_id"],
                    "member": member["name"],
                    "party": member["political_party"],
                    "status": status,
                    "replaced_by": replaced_by,
                })

        all_meetings_df.at[index, "read_status"] = "processed"
        all_meetings_df.to_csv(cache_path, index=False)

    attendance_df = pd.DataFrame(attendance_rows, columns=[
        "date", "paragraph", "representative_id", "member",
        "party", "status", "replaced_by",
    ])
    logger.info("Skapade n?rvarotabell med %d rader", len(attendance_df))
    print(attendance_df)
    return attendance_df


if __name__ == "__main__":
    main()
