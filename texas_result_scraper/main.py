from __future__ import annotations
from typing import TypeVar, Generic, Optional, Any
import json
from pathlib import Path
import csv
import itertools
from time import sleep

from sqlalchemy.orm.exc import StaleDataError
from sqlmodel import Session, text
from pydantic import BaseModel

from texas_result_scraper.scraper import ElectionResultTicker, TomlReader, model
from texas_result_scraper.flat_file import GitHubFile
from texas_result_scraper.utils import db, TomlReader

# TODO: Fix github flat file functionaility to output as a SQLModel object without Instrumented Lists
# TODO: Fix Scraper.py to upload pytdanticmodels of SQLModel, without relationships. Eliminate circular loading of data. 


# P2024_ELECTION_RESULTS = ElectionResultTicker(election_id=49664, engine=psql_engine)
P2024_ELECTION_RESULTS = ElectionResultTicker(election_id=49664)
# P2024_ELECTION_RESULTS.create_file()
# P2024_ELECTION_RESULTS.pull_data()
# P2024_ELECTION_RESULTS.create_models()
# version_data = P2024_ELECTION_RESULTS.version_no.model_dump()

# with open(Path(__file__).parent / 'model_schemas' / 'county_json.json', 'w') as f:
#     json.dump(P2024_ELECTION_RESULTS.county_raw, f, indent=4)

# with open(Path(__file__).parent / 'model_schemas' / 'county_json.json', 'r') as f:
#     county_data = json.load(f)


make_flat_file = GitHubFile(P2024_ELECTION_RESULTS)
make_flat_file.github_flat_file()
make_flat_file.write()
output = make_flat_file.read()

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
