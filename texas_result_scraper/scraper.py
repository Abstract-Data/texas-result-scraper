from typing import Dict, List, ClassVar, Type, Generator, Optional
from pathlib import Path
from dataclasses import dataclass, field
from time import sleep
from sqlmodel import SQLModel, Session, select, text
from sqlalchemy.engine import Engine
from sqlalchemy import event

import cfscrape
from texas_result_scraper.utils.toml_reader import TomlReader
from texas_result_scraper.result_db import Session
import texas_result_scraper.result_validator as validators

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


def populate_office_details(mapper, connection, target):
    if target.race_data:
        session = Session.object_session(target)
        race_details = session.query(validators.RaceDetails).filter_by(id=target.race_data.id).first()
        if race_details:
            target.office_type = race_details.office_type
            target.office_district = race_details.office_district

@dataclass
class ElectionResultTicker:
    election_id: int
    version_no: validators.ResultVersionNumber = field(default=None)
    # logger: ClassVar[Logger] = Logger(module_name="class:ElectionResultTicker")
    scraper: ClassVar[cfscrape.CloudflareScraper] = cfscrape.create_scraper()
    statewide_data: List[validators.StatewideOfficeSummary] = field(default_factory=list)
    county_data: List = field(default_factory=list)
    candidate_cache = {}  # Add a cache for candidates
    race_cache = {}  # Add
    endorsements: List[validators.CandidateEndorsements] = field(default=None)
    url_file: Dict[str, str] = field(init=False)
    engine: Optional[Engine] = None

    def __post_init__(self):
        self.url_file = TomlReader(Path(__file__).parent / 'texas_results_urls.toml').data

    def _get_newest_version(self):
        _version = self.scraper.get(
            self.url_file['result_version_url'].format(
                electionId=self.election_id
            )
        ).json()
        self.version_no = validators.ResultVersionNumber(
            id=_version['___versionNo'],
            election_date=_version['elecDate'],
            election_id=self.election_id,
        )
        return self

    def _get_county_data(self):
        _county_data = list(self.scraper.get(
            self.url_file[
                'county_url'
            ]
            .format(
                electionId=self.election_id,
                versionNo=self.version_no.id
            )
        ).json().values())
        return _county_data

    def _setup_county_data(self):
        for _county in self._get_county_data():
            c = validators.County(
                name=_county['N'],
                registered_voters=_county['TV'],
                color=_county['C'],
                version_number=self.version_no,
            )

            c.summary = validators.CountySummary(
                **_county['Summary'],
                county_name=c.name,
            )
            for race in _county['Races'].values():
                race_id = race['OID']
                if race_id not in self.race_cache:
                    _race_data = validators.RaceDetails(
                        id=race_id,
                        office=race['ON'],
                        total_votes=race['T'],
                        ballot_order=race['O'],
                        precincts_reporting=race['PR'],
                        registered_voters=race['OTRV'],
                        total_precincts=race['TPR'],
                    )
                    self.race_cache[race_id] = _race_data
                else:
                    _race_data = self.race_cache[race_id]

                for candidate in race['C'].values():
                    # Use cache to avoid duplicate candidates
                    candidate_id = candidate['id']
                    if candidate_id not in self.candidate_cache:
                        _candidate_name = validators.CandidateName(
                            id=candidate_id,
                            full_name=candidate['N'],
                            party=candidate['P']
                        )
                        self.candidate_cache[candidate_id] = _candidate_name
                    else:
                        _candidate_name = self.candidate_cache[candidate_id]

                    # Add relationships
                    if c not in _candidate_name.county_name:
                        _candidate_name.county_name.append(c)

                    # Add results
                    _candidate_results = validators.CandidateCountyResults(
                        color=candidate['C'],
                        early_votes=candidate['EV'],
                        total_votes=candidate['V'],
                        percent=candidate['PE'],
                        ballot_order=candidate['O'],
                    )
                    _candidate_name.county_results.append(_candidate_results)
                    if _race_data not in _candidate_name.race:
                        _race_data.candidates.append(_candidate_name)
                c.races.append(_race_data)
            self.county_data.append(c)
        self.version_no.county = self.county_data
        return self

    def _get_statewide_data(self):
        _statewide_data = self.scraper.get(
            self.url_file[
                'office_url'
            ]
            .format(
                electionId=self.election_id,
                versionNo=self.version_no.id
            )
        ).json()['OS']
        return _statewide_data

    def _setup_statewide_data(self):
        for office in self._get_statewide_data():
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

    def _update_data(self):
        self.get_newest_version()
        sleep(5)
        return self
    
    def github_flat_file(self):
        self._get_newest_version()
        self._setup_county_data()
        self._setup_statewide_data()
        _version_data = validators.ResultVersionPublicModel(
            id=self.version_no.id,
            election_id=self.election_id,
            election_date=self.version_no.election_date,
            county=self.county_data,
            statewide=self.statewide_data
        )
        with open(Path(__file__).parent / 'data'/ f'tx-{self.election_id}-{self.version_no.id}.json', 'w') as f:
            f.write(_version_data.model_dump_json())
        return self
    

    def initial_setup(self):
        self._get_newest_version()
        self._setup_county_data()
        self._setup_statewide_data()
        SQLModel.metadata.create_all(bind=self.engine)
        # self.logger.warning("func:update_database ENABLED")
        with Session(self.engine) as session:
            try:
                # First add version number
                session.add(self.version_no)

                # Cache to track what we've already added
                processed_races = set()
                processed_candidates = set()
                processed_counties = set()

                # Process each county
                for county in self.county_data:
                    if county.name not in processed_counties:
                        # Add county summary first
                        if county.summary:
                            session.add(county.summary)

                        # Process races
                        for race in county.races:
                            if race.id not in processed_races:
                                session.add(race)
                                processed_races.add(race.id)

                                # Process candidates for this race
                                for candidate in race.candidates:
                                    if candidate.id not in processed_candidates:
                                        session.add(candidate)
                                        processed_candidates.add(candidate.id)

                                        # Add candidate results
                                        for result in candidate.county_results:
                                            session.add(result)

                        # Add the county after its relationships
                        session.add(county)
                        processed_counties.add(county.name)
                # Commit everything at once at the end
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Error during database update: {e}")
                raise

        # self.logger.info("Database updated")
    def refresh_data(self):
        self._get_newest_version()
        self._get_county_data()
        self._get_statewide_data()
        with Session(self.engine) as session:
            session.merge(self.version_no)
            for county in self.county_data:
                _existing_county = session.exec(select(validators.County).where(validators.County.name == county.name)).first()
                _existing_county.summary = county.summary

                for race in county.races:
                    _existing_race = session.exec(select(validators.RaceDetails).where(validators.RaceDetails.id)).first()
                    for candidate in race.candidates:
                        _existing_candidate = session.exec(select(validators.Candidate).where(validators.Candidate.id == candidate.id)).first()
                        _existing_candidate.county_name.append(_existing_county)
                        for result in candidate.county_results:
                            _existing_candidate.county_results.append(result)
                            session.add(_existing_candidate)
                        session.add(_existing_candidate)
                    session.add(_existing_race)
                session.add(_existing_county)
            session.commit()

            for office in self.statewide_data:
                _existing_office = session.exec(select(validators.StatewideOfficeSummary).where(validators.StatewideOfficeSummary.id == office.id)).first()
                for candidate in office.candidates:
                    _existing_candidate = session.exec(select(validators.StatewideCandidateSummary).where(validators.StatewideCandidateSummary.id == candidate.id)).first()
                    _existing_candidate.office_id = _existing_office.id
                    _existing_candidate.version_id = _existing_office.version_id
                    _existing_candidate.candidate_data = candidate.candidate_data
                    session.add(_existing_candidate)
                session.add(_existing_office)
            session.commit()

            #     for race in county.races:
            #         _existing_race = session.exec(select(validators.RaceDetails).where(validators.RaceDetails.id == race.id)).first()
            #
            #         for candidate in race.candidates:
            #             _existing_candidate = session.exec(select(validators.Candidate).where(validators.Candidate.id == candidate.id)).first()
            #             _existing_candidate.county_name.append(_existing_county)
            #             for result in candidate.county_results:
            #                 _existing_candidate.county_results.append(result)
            #             _existing_race.candidates.append(_existing_candidate)
            #             session.refresh(_existing_candidate)
            #         session.refresh(_existing_race)
            # session.commit()



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