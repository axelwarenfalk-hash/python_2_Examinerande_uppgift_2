import pandas as pd
import logging


logger = logging.getLogger(__name__)


def make_all_members_dataframe(json_data):
    all_members_df = pd.json_normalize(json_data["Items"], sep="_")

    all_members_df = all_members_df[
        [
            'Id',
            'Name',
            'PoliticalParty_Name',
            'PoliticalParty_Id'
        ]
    ]

    all_members_df = all_members_df.rename(columns={
        'Name': 'name',
        'Id': 'representative_id',
        'PoliticalParty_Name': 'political_party',
        'PoliticalParty_Id': 'political_party_id'
    })

    logger.info("Normaliserade %d ledamöter", len(all_members_df))
    return all_members_df


def make_all_roles_dataframe(json_data):
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

    logger.info("Normaliserade %d rollrader", len(all_roles_df))
    return all_roles_df


def merge_all_members_with_all_roles(members_df, roles_df):
    merged_df = members_df.merge(
        roles_df,
        on='representative_id',
        how='left'
    )

    logger.info(
        "Slog ihop ledamöter och roller: %d personer, %d rollrader, %d resultat",
        len(members_df),
        len(roles_df),
        len(merged_df),
    )
    return merged_df


def separate_members_from_replacements(df_all_members):

    is_member = df_all_members["council_number"].between(1, 61)

    members_df = df_all_members.loc[is_member].copy()
    members_df = members_df.sort_values("council_number")
    replacements_df = df_all_members.loc[~is_member].copy()
    replacements_df = replacements_df.sort_values("council_number")

    logger.info(
        "Delade upp rådata: %d ledamotsrader, %d ersättarrader",
        len(members_df),
        len(replacements_df),
    )
    return members_df, replacements_df

