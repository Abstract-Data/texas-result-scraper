from typing import Dict, List, ClassVar, Type, Generator
import cfscrape
import texas_result_scraper.result_validator as validators
from pathlib import Path
from texas_result_scraper.utils.toml_reader import TomlReader
from dataclasses import dataclass, field
from time import sleep
from texas_result_scraper.result_db import Session, engine
from sqlmodel import SQLModel


EXAMPLES = (47009, 242), (47010, 278), (49681, 665), (49666, 661)


# @dataclass
# class CountyValidationModels:
#     models: List[validators.County]
#     races: List[validators.RaceDetails] = field(init=False)
#     candidates: List[validators.Candidate] = field(init=False)
#     summaries: List[validators.CountySummary] = field(init=False)
#
#     def __post_init__(self):
#         self.races = [
#             race for model in self.models for race in model.races.values()
#         ]
#         self.candidates = [
#             candidate for race in self.races for candidate in race.candidates.values() if candidate
#         ]
#         self.summaries = [model.summary for model in self.models]
#
#
# @dataclass
# class StatewideValidationModels:
#     models: List[validators.StatewideOfficeSummary]
#     candidates: List[validators.StatewideCandidateSummary] = field(init=False)
#     endorsements: List[validators.CandidateEndorsements] = field(init=False)
#
#     def __post_init__(self):
#         self.endorsements = [
#             candidate.endorsements for model in self.models for candidate in model.candidates if candidate.endorsements
#         ]
#         self.candidates = [
#             candidate for model in self.models for candidate in model.candidates
#         ]


@dataclass
class ElectionResultTicker:
    election_id: int
    version_no: validators.ResultVersionNumber = field(default=None)
    # logger: ClassVar[Logger] = Logger(module_name="class:ElectionResultTicker")
    scraper: ClassVar[cfscrape.CloudflareScraper] = cfscrape.create_scraper()
    statewide_data: List[validators.StatewideOfficeSummary] = field(default_factory=list)
    county_data: List = field(default_factory=list)
    endorsements: List[validators.CandidateEndorsements] = field(default=None)
    url_file: Dict[str, str] = field(init=False)
    ready_to_load: List[SQLModel] = field(default=None)

    def __post_init__(self):
        self.url_file = TomlReader(Path(__file__).parent / 'texas_results_urls.toml').data

    def get_newest_version(self):
        _version = self.scraper.get(
            self.url_file['result_version_url'].format(
                electionId=self.election_id
            )
        ).json()
        self.version_no = validators.ResultVersionNumber(
            id=_version['___versionNo'],
            election_date=_version['elecDate']
        )
        return self

    def get_county_data(self):
        _county_data = list(self.scraper.get(
            self.url_file[
                'county_url'
            ]
            .format(
                electionId=self.election_id,
                versionNo=self.version_no.id
            )
        ).json().values())
        for _county in _county_data:
            county_races = []
            for race in _county['Races'].values():
                _candidates = [validators.Candidate(
                    id=x['id'],
                    full_name=x['N'],
                    party=x['P'],
                    color=x['C'],
                    early_votes=x['EV'],
                    total_votes=x['V'],
                    percent=x['PE'],
                    ballot_order=x['O'],
                ) for x in race['C'].values()]
                county_races.append(
                    validators.RaceDetails(
                        id=race['OID'],
                        office=race['ON'],
                        total_votes=race['T'],
                        ballot_order=race['O'],
                        precincts_reporting=race['PR'],
                        registered_voters=race['OTRV'],
                        total_precincts=race['TPR'],
                        candidates=_candidates
                    )
                )
            c = validators.County(
                name=_county['N'],
                registered_voters=_county['TV'],
                color=_county['C'],
                races=county_races,
                version_number=self.version_no,
            )
            c.summary = validators.CountySummary(
                **_county['Summary'],
                county_name=c.name,
            )
            self.county_data.append(c)
        # self.version_no.county = self.county_data
        return self

    def get_statewide_data(self):
        _statewide_data = self.scraper.get(
            self.url_file[
                'office_url'
            ]
            .format(
                electionId=self.election_id,
                versionNo=self.version_no.id
            )
        ).json()['OS']

        for office in _statewide_data:
            office_summary = validators.StatewideOfficeSummary(
                id=office['OID'],
                name=office['ON'],
                version_id=self.version_no.id,
                candidates=[
                    validators.StatewideCandidateSummary(
                        name=x['N'],
                        party=x['P'],
                        color=x['C'],
                        total_votes=x['T'],
                        ballot_order=x['O'],
                        office_id=office['OID'],
                    ) for x in office['C']
                ]
            )
            office_summary.version_number = self.version_no
            for candidate in office_summary.candidates:
                for county in self.county_data:
                    for each_race in county.races:
                        office_summary.race_data = each_race
                        for each_candidate in each_race.candidates:
                            if each_candidate.full_name == candidate.name:
                                # candidate.candidate_id = each_candidate.id
                                candidate.candidate_data = each_candidate
            self.statewide_data.append(office_summary)
        self.version_no.statewide = self.statewide_data
        return self

    def update_data(self):
        self.get_newest_version()
        self.get_county_data()
        self.get_statewide_data()
        sleep(5)
        return self

    def update_database(self):
        SQLModel.metadata.create_all(bind=engine)
        # self.logger.warning("func:update_database ENABLED")
        with Session(engine) as session:
            session.add_all(self.version_no.statewide)
            session.commit()
        # self.logger.info("Database updated")

    # def auto_refresh(self):
    #     # self.logger.warning("func:auto_refresh ENABLED")
    #     while True:
    #         current_time = datetime.now()
    #         self.get_newest_version()
    #         self.ready_to_load = list(self.create_db_models())
    #         print("Ready to load")
    #         self.update_database()
    #         # self.logger.info(f"Results updated at {current_time.strftime('%H:%M:%S')}")
    #         if current_time.hour <= 3:
    #             # self.logger.warning("Current time is after 3 am. Stopping auto refresh.")
    #             break
    #         sleep(60)  # wait for 60 seconds before checking again