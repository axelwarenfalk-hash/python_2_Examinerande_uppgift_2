"""Hämta grunddata och dela upp förtroendevalda i ledamöter och ersättare."""

from pathlib import Path
from typing import Any

import pandas as pd
import logging

from .config import ReportConfig
from .io import get_api_json, read_json, save_json


logger = logging.getLogger(__name__)


def select_members_from_term_start(
    members_df: pd.DataFrame, term_start: pd.Timestamp
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Behåll nu listade ledamöter vars registrerade uppdrag omfattar mandatperiodens start."""
    starts = pd.to_datetime(members_df["date_from"])
    ends = pd.to_datetime(members_df["date_to"])
    included = starts.le(term_start) & (ends.isna() | ends.ge(term_start))
    return members_df.loc[included].copy(), members_df.loc[~included].copy()


def make_all_representatives_dataframe(json_data: dict[str, Any]) -> pd.DataFrame:
    """Plocka ut personernas id, namn och parti från API-svaret."""
    all_representatives_df = pd.json_normalize(json_data["Items"], sep="_")

    all_representatives_df = all_representatives_df[
        [
            'Id',
            'Name',
            'PoliticalParty_Name',
            'PoliticalParty_Id'
        ]
    ]

    all_representatives_df = all_representatives_df.rename(columns={
        'Name': 'name',
        'Id': 'representative_id',
        'PoliticalParty_Name': 'political_party',
        'PoliticalParty_Id': 'political_party_id'
    })

    logger.info("Normaliserade %d personer", len(all_representatives_df))
    return all_representatives_df


def make_all_roles_dataframe(json_data: list[dict[str, Any]]) -> pd.DataFrame:
    """Skapa rolltabellen och omvandla uppdragens start- och slutdatum."""
    all_roles_df = pd.json_normalize(json_data, sep="_")

    all_roles_df = all_roles_df[
        [
            'RepresentativeId',
            'Role',
            'DateFrom',
            'DateTo',
            'Number',
            'State',
        ]
    ]

    all_roles_df = all_roles_df.rename(columns={
        'RepresentativeId': 'representative_id',
        'Role': 'role',
        'DateFrom': 'date_from',
        'DateTo': 'date_to',
        'Number': 'council_number',
        'State': 'state'

    })
    
    all_roles_df["date_from"] = pd.to_datetime(all_roles_df["date_from"])
    all_roles_df["date_to"] = pd.to_datetime(all_roles_df["date_to"])

    logger.info("Normaliserade %d rollrader", len(all_roles_df))
    return all_roles_df


def merge_all_representatives_with_all_roles(
    df_all_representatives: pd.DataFrame, roles_df: pd.DataFrame
) -> pd.DataFrame:
    """Koppla roller till person-id och behåll även personer utan matchande roll."""
    merged_df = df_all_representatives.merge(
        roles_df,
        on='representative_id',
        how='left'
    )

    logger.info(
        "Slog ihop ledamöter och roller: %d personer, %d rollrader, %d resultat",
        len(df_all_representatives),
        len(roles_df),
        len(merged_df),
    )
    return merged_df


def separate_members_from_replacements(df_all_representatives: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returnera ledamöter med nummer 1–61 och övriga som ersättare."""

    is_member = df_all_representatives["council_number"].between(1, 61)

    members_df = df_all_representatives.loc[is_member].copy()
    members_df = members_df.sort_values("council_number")

    replacements_df = df_all_representatives.loc[~is_member].copy()
    replacements_df = replacements_df.sort_values("council_number")

    logger.info(
        "Delade upp rådata: %d ledamotsrader, %d ersättarrader",
        len(members_df),
        len(replacements_df),
    )
    return members_df, replacements_df


def load_council(cache_path: Path, use_cache: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Läs API-data eller cache och returnera tabeller för ledamöter och ersättare."""
    if use_cache and cache_path.exists():
        data = read_json(cache_path)
        logger.info("Läser rådets grunddata från cache")
    else:
        data = {
            "representatives": get_api_json(ReportConfig.api_url_all_council_representatives),
            "roles": get_api_json(ReportConfig.api_url_all_council_roles),
        }
    if not isinstance(data["representatives"], dict):
        raise TypeError("Förväntade en ordbok med personuppgifter")
    if not isinstance(data["roles"], list):
        raise TypeError("Förväntade en lista med roller")
    representatives = make_all_representatives_dataframe(data["representatives"])
    roles = make_all_roles_dataframe(data["roles"])
    save_json(data, cache_path)
    combined = merge_all_representatives_with_all_roles(representatives, roles)
    return separate_members_from_replacements(combined)

