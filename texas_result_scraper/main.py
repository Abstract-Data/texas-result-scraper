from __future__ import annotations
from texas_result_scraper.scraper import ElectionResultTicker, TomlReader
from texas_result_scraper.result_db import engine, psql_engine
from pathlib import Path
import csv
import itertools
from sqlalchemy.orm.exc import StaleDataError
from time import sleep
from sqlmodel import Session, text

P2024_ELECTION_RESULTS = ElectionResultTicker(election_id=49664, engine=psql_engine)
P2024_ELECTION_RESULTS.initial_setup()

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
