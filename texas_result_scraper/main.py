from __future__ import annotations
from typing import TypeVar, Generic, Optional, Any
import json
from pathlib import Path
import csv
import itertools
from time import sleep
import pandas as pd

from sqlalchemy.orm.exc import StaleDataError
from sqlmodel import Session, text
from pydantic import BaseModel

from texas_result_scraper.scraper import ElectionResultTicker, TomlReader, model
from texas_result_scraper.flat_file import GitHubFile
from texas_result_scraper.utils import db, TomlReader

# TODO: Fix github flat file functionaility to output as a SQLModel object without Instrumented Lists
# TODO: Fix Scraper.py to upload pytdanticmodels of SQLModel, without relationships. Eliminate circular loading of data. 


P2024_ELECTION_RESULTS = ElectionResultTicker(election_id=49664)
race_list = list(x.flatten() for x in P2024_ELECTION_RESULTS.races.values())
races = []
for x in race_list:
    for y in x:
        races.append(y)

race_df = pd.DataFrame(races).drop_duplicates()
make_flat_file = GitHubFile(P2024_ELECTION_RESULTS)
make_flat_file.github_flat_file()
make_flat_file.create_csv_files()

results_ct = pd.crosstab(
    index=[
    race_df['office_type'], race_df['office'], race_df['candidate'], race_df['party']],
    columns=race_df['county'],
    values=race_df['total_votes'],
    aggfunc='sum',
    margins=True
    )
results_ct.to_json(Path.home() / 'Downloads/multiindex.json')

# office_results = data.groupby(['office', 'office_type', 'office_district', 'candidate', 'party']).agg(
#     early_votes=('early_votes', 'sum'),
#     election_day_votes=('election_day_votes', 'sum'),
#     total_votes=('total_votes', 'sum'),
#     percent_votes=('percent_votes', 'mean')
# ).reset_index()

# with Session(engine) as session:
#     session.execute(
#         text("""
#         CREATE OR REPLACE VIEW result_counts AS
#         SELECT
#         office_type,
#         COUNT(CASE WHEN winner_party = 'R' THEN 1 END) AS Republican_Wins,
#         COUNT(CASE WHEN winner_party = 'D' THEN 1 END) AS Democrat_Wins
#         FROM
#         statewideofficesummary
#         GROUP BY
#         office_type
#         ORDER BY
#         Republican_Wins DESC;
#     """)
#     )
#     session.commit()
# candidate_list = []
# counties = P2024_ELECTION_RESULTS.version_no.county
# for county in counties:
#     for race in county.races:
#         for candidate in race.candidates:
#             if candidate.id == 3192:
#                 candidate_list.append(candidate)
