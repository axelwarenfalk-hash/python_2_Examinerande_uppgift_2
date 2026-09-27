from . import *
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

cache_path = Path("data/meeting_protocol_links.csv")

def main():
    config_logging()
    logger.info("Startar inläsning av kommunfullmäktiges grunddata")

    # Hämtar namn och parti på alla ledamöter och erssättare från malmöstads api
    all_members_json = get_api_json(ReportConfig.api_url_all_council_members)
    all_members_df = make_all_members_dataframe(all_members_json)

    # Hämtar alla roller på ledamöter och erssättare från malmöstads andra api
    all_roles_json = get_api_json(ReportConfig.api_url_all_council_roles)
    all_roles_df = make_all_roles_dataframe(all_roles_json)

    # Slår ihop både namn och roll df:erna
    all_members_with_roles_df = merge_all_members_with_all_roles(all_members_df, all_roles_df)

    # Separerar på ledamöter och ersättare till två olika dfs
    members_df, replacements_df = separate_members_from_replacements(all_members_with_roles_df)
    logger.info(
        "Grunddata klar: %d ledamotsrader och %d ersättarrader",
        len(members_df),
        len(replacements_df),
    )

    
    # Hämtar html från meetingssidan
    all_meetings_html = get_page_html(ReportConfig.url_all_meetings)
    # tar ut rätt länkar från hmtl och lägger i df hela länkadressen
    all_meetings_df = find_meeting_links(all_meetings_html, ReportConfig.base_url)

    if cache_path.exists():
        all_meetings_df = pd.read_csv(cache_path, parse_dates=["date"])
    else:
        all_meetings_df["pdf_url"] = all_meetings_df["url"].apply(find_pdf_links)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        all_meetings_df.to_csv(cache_path, index=False)

    
    


    # All fast kod klar. fortsätt med itteration genom länkar




if __name__ == "__main__":
    main()