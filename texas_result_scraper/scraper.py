from __future__ import annotations
from typing import Dict, List, ClassVar, Type, Generator
import cfscrape
import texas_result_scraper.validators as validators
import texas_result_scraper.models as models
from pathlib import Path
from state_voterfiles.utils.readers.toml_reader import TomlReader
from datetime import datetime
from dataclasses import dataclass, field
from time import sleep
from .result_db import Session, engine
from sqlmodel import SQLModel
import itertools
from icecream import ic


EXAMPLES = (47009, 242), (47010, 278), (49681, 665), (49666, 661)


@dataclass
class CountyValidationModels:
    models: List[validators.County]
    races: List[validators.Race] = field(init=False)
    candidates: List[validators.Candidate] = field(init=False)
    summaries: List[validators.Summary] = field(init=False)

    def __post_init__(self):
        self.races = [
            race for model in self.models for race in model.races.values()
        ]
        self.candidates = [
            candidate for race in self.races for candidate in race.candidates.values() if candidate
        ]
        self.summaries = [model.summary for model in self.models]
    
    
@dataclass
class StatewideValidationModels:
    models: List[validators.StatewideOfficeSummary]
    candidates: List[validators.StatewideCandidateSummary] = field(init=False)
    endorsements: List[validators.CandidateEndorsements] = field(init=False)
    
    def __post_init__(self):
        self.endorsements = [
            candidate.endorsements for model in self.models for candidate in model.candidates if candidate.endorsements
        ]
        self.candidates = [
            candidate for model in self.models for candidate in model.candidates
        ]


@dataclass
class ElectionResultTicker:
    election_id: int
    logger: ClassVar[Logger] = Logger(module_name="class:ElectionResultTicker")
    scraper: ClassVar[cfscrape.CloudflareScraper] = cfscrape.create_scraper()
    statewide_data: StatewideValidationModels = field(default=None)
    county_data: CountyValidationModels = field(default=None)
    endorsements: List[validators.CandidateEndorsements] = field(default=None)
    url_file: Dict[str, str] = field(init=False)
    ready_to_load: List[models.SQLModel] = field(default=None)

    def __post_init__(self):
        self.url_file = TomlReader(Path(__file__).parents[2] / 'texas_results_urls.toml')()

    def get_newest_version(self) -> ElectionResultTicker:
        version = validators.ResultVersionNumber.model_validate(
            self.scraper.get(
                self.url_file['result_version_url'].format(
                    electionId=self.election_id
                )
            )
            .json()
        )
        sleep(5)

        self.county_data = CountyValidationModels(
            models=[
                validators.County.model_validate(
                    county
                ) for county in self.scraper.get(
                    self.url_file[
                        'county_url'
                    ]
                    .format(
                        electionId=self.election_id,
                        versionNo=version.id
                    )
                )
                .json()
                .values()
            ]
        )
        sleep(5)

        self.statewide_data = StatewideValidationModels(
            models=[
                validators.StatewideOfficeSummary.model_validate(
                    office
                ) for office in self.scraper.get(
                    self.url_file[
                        'office_url'
                    ]
                    .format(
                        electionId=self.election_id,
                        versionNo=version.id
                    )
                )
                .json()[
                    'OS'
                ]
            ]
        )
        return self

    def create_db_models(self):
        record_types = itertools.chain([
            self.statewide_data.endorsements,
            self.statewide_data.models,
            self.statewide_data.candidates,
            self.county_data.models,
            self.county_data.summaries,
            self.county_data.candidates,
            self.county_data.races
        ])
        for _type in record_types:
            for record in _type:
                if isinstance(record, validators.CandidateEndorsements):
                    yield models.CandidateEndorsementsORM.model_validate(record)
                    ic("Endorsement record validated")
                if isinstance(record, validators.StatewideCandidateSummary):
                    yield models.StatewideCandidateSummaryORM.model_validate(record)
                    ic("Statewide Candidate Summary record validated")
                if isinstance(record, validators.StatewideOfficeSummary):
                    yield models.StatewideOfficeSummaryORM.model_validate(record)
                    ic("Statewide Office Summary record validated")
                if isinstance(record, validators.County):
                    yield models.CountyORM.model_validate(record)
                    ic("County record validated")
                if isinstance(record, validators.Candidate):
                    yield models.CandidateORM.model_validate(record)
                    ic("Candidate record validated")
                if isinstance(record, validators.Race):
                    yield models.RaceORM.model_validate(record)
                    ic("Race record validated")
                if isinstance(record, validators.County):
                    yield models.CountyORM.model_validate(record)
                    ic("County record validated")

    def update_database(self):
        SQLModel.metadata.create_all(bind=engine)
        self.logger.warning("func:update_database ENABLED")
        with Session(engine) as session:
            for record in self.ready_to_load:
                print("Merging record")
                if isinstance(record, models.CandidateEndorsementsORM):
                    session.merge(record)
                else:
                    print(f"adding {record}")
                    session.add(record)
            session.commit()
        self.logger.info("Database updated")

    def auto_refresh(self):
        self.logger.warning("func:auto_refresh ENABLED")
        while True:
            current_time = datetime.now()
            self.get_newest_version()
            self.ready_to_load = list(self.create_db_models())
            print("Ready to load")
            self.update_database()
            self.logger.info(f"Results updated at {current_time.strftime('%H:%M:%S')}")
            if current_time.hour <= 3:
                self.logger.warning("Current time is after 3 am. Stopping auto refresh.")
                break
            sleep(60)  # wait for 60 seconds before checking again