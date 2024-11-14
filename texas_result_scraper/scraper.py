import abc
from typing import Dict, List, ClassVar, Type, Generator, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from time import sleep
from sqlmodel import SQLModel, Session, select, text
from sqlalchemy.engine import Engine
from sqlalchemy import event

import cfscrape
from texas_result_scraper.utils.toml_reader import TomlReader
from texas_result_scraper.result_db import Session
import texas_result_scraper.result_models as model
import texas_result_scraper.result_bases as base

EXAMPLES = (47009, 242), (47010, 278), (49681, 665), (49666, 661)

# TOD0: Create methods to export data as a flat file and avoid circular loading. May need to setup both processes as their own classes.
# TODO: Create vars for FileTicker for race and candidate details, and add them to the setup methods.
# TODO: Fix the FileTicker so that all races and results are paired to each county instead of being in a separate list.

def populate_office_details(self, mapper, connection, target):
    if target.race_data:
        session = Session.object_session(target)
        race_details = session.query(self.model.RaceDetails).filter_by(id=target.race_data.id).first()
        if race_details:
            target.office_type = race_details.office_type
            target.office_district = race_details.office_district

@dataclass
class TickerVars:
    election_id: int
    version_no: base.ResultVersionNumberBase = field(default=None)
    models: model.ModelGroup = model.DBModels
    scraper: ClassVar[cfscrape.CloudflareScraper] = cfscrape.create_scraper()
    url_file: Dict[str, str] = field(init=False)
    state_raw: Dict = field(default_factory=dict)
    county_raw: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.url_file = TomlReader(Path(__file__).parent / 'texas_results_urls.toml').data


@dataclass
class TickerFuncs(TickerVars, abc.ABC):
    candidate_cache = {}  # Add a cache for candidates
    race_cache = {}  # Add

        
    def create_file(self):
        self.as_file = True
        self.models = model.FileModels
        return self
    
    def _get_newest_version(self):
        _version = self.scraper.get(
            self.url_file['result_version_url'].format(
                electionId=self.election_id
            )
        ).json()
        self.version_no = self.models.ResultVersionNumber(
            version_id=_version['___versionNo'],
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
                versionNo=self.version_no.version_id
            )
        ).json().values())
        self.county_raw = _county_data
        return self.county_raw
    
    
    def _get_statewide_data(self):
        _statewide_data = self.scraper.get(
            self.url_file[
                'office_url'
            ]
            .format(
                electionId=self.election_id,
                versionNo=self.version_no.version_id
            )
        ).json()['OS']
        self.state_raw = _statewide_data
        return self.state_raw
        
    def pull_data(self):
        self._get_newest_version()
        self._get_county_data()
        self._get_statewide_data()
        return self
    
    def create_models(self):
        self._setup_county_data()
        self._setup_statewide_data()
        return self
    
    @abc.abstractmethod
    def _setup_county_data(self):
        pass
    
    @abc.abstractmethod
    def _setup_statewide_data(self):
        pass

    
@dataclass
class DataBaseTickerFuncs(TickerFuncs):
    statewide_data: List[base.StatewideOfficeSummaryBase] = field(default_factory=list)
    county_data: List = field(default_factory=list)
    engine: Optional[Engine] = None
    

    def _setup_county_data(self):
        for _county in self._get_county_data():
            c = self.models.County(
                name=_county['N'],
                registered_voters=_county['TV'],
                color=_county['C'],
                version_number=self.version_no,
            )

            c.summary = self.models.CountySummary(
                **_county['Summary'],
                county_name=c.name,
            )
            for race in _county['Races'].values():
                race_id = race['OID']
                if race_id not in self.race_cache:
                    _race_data = self.models.RaceDetails(
                        race_id=race_id,
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
                        _candidate_name = self.models.CandidateName(
                            candidate_id=candidate_id,
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
                    _candidate_results = self.models.CandidateCountyResults(
                        color=candidate['C'],
                        early_votes=candidate['EV'],
                        total_votes=candidate['V'],
                        percent=candidate['PE'],
                        ballot_order=candidate['O'],
                    )
                    _candidate_name.county_results.append(_candidate_results)
                    if not _candidate_name.race:
                        _race_data.candidates.append(_candidate_name)
                c.races.append(_race_data)
            self.county_data.append(c)
        self.version_no.county = self.county_data
        return self

    def _setup_statewide_data(self):
        for office in self._get_statewide_data():
            office_summary = self.models.StatewideOfficeSummary(
                office_id=office['OID'],
                name=office['ON'],
                version_id=self.version_no.version_id,
                candidates=[
                    self.models.StatewideCandidateSummary(
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
                                candidate.candidate_data.append(each_candidate)
            self.statewide_data.append(office_summary)
        self.version_no.statewide = self.statewide_data
        return self


@dataclass
class FileTickerFuncs(TickerFuncs):
    counties: Dict[str, Any] = field(default_factory=dict)
    races: dict[str, Any] = field(default_factory=dict)
    candidates: dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.models = model.FileModels
        
    def _setup_county_data(self):
        for _county in self._get_county_data():
            c = self.models.County(
                name=_county['N'],
                registered_voters=_county['TV'],
                color=_county['C'],
                version_number=self.version_no.version_id,
            )
            d = _county['Summary']
            c.summary = self.models.CountySummary(
                county_name=c.name,
                precincts_reporting=d['PRR'],
                total_precincts=d['PRP'],
                percent_reporting=d['P'],
                registered_voters=d['RV'],
                votes_counted=d['VC'],
                turnout_percent=d['VT'],
                poll_locations=d['NPL'],
                poll_locations_reporting=d['PLR'],
                poll_locations_percent=d['PLP'],
            )
            # c.summary = self.models.CountySummary(
            #     **_county['Summary'],
            #     county_name=c.name,
            # )
            _county_details = {c.name: c}
            self.counties.update(_county_details)
            
            for race in _county['Races'].values():
                race_id = race['OID']
                _state_race_data = self.races.get(race_id)
                if not _state_race_data:
                    _state_race_data = self.models.RaceDetails(
                        race_id=race_id,
                        office=race['ON'],
                    )
                    self.races[race_id] = _state_race_data
                    
                _county_race_data = next((x for x in _state_race_data.counties if x.county == c.name), None)
                if not _county_race_data:
                    _county_race_data = self.models.CountyRaceDetails(
                        county=c.name,
                        race_id=race_id,
                        county_total_votes=race['T'],
                        county_ballot_order=race['O'],
                        county_precincts_reporting=race['PR'],
                        county_registered_voters=race['OTRV'],
                        county_precincts=race['TPR'],
                    )
                _state_race_data.counties.append(_county_race_data)
                    
                for candidate in race['C'].values():
                    # Use cache to avoid duplicate candidates
                    _candidate_id = candidate['id']
                    _candidate_idx = next(
                        (i for i, x in enumerate(self.races[race_id].candidates) 
                         if x.candidate_id == _candidate_id), 
                        None
                        )
                    if _candidate_idx is not None:
                        _candidate_name = self.races[race_id].candidates.pop(_candidate_idx)
                    else:
                        _candidate_name = self.models.CandidateName(
                            candidate_id=_candidate_id,
                            full_name=candidate['N'],
                            party=candidate['P']
                        )
                        
                    # Add results
                    _candidate_results = self.models.CandidateCountyResults(
                        county=c.name,
                        color=candidate['C'],
                        early_votes=candidate['EV'],
                        total_votes=candidate['V'],
                        percent=candidate['PE'],
                        ballot_order=candidate['O'],
                    )
                    _candidate_name.county_results.append(_candidate_results)
                    # self.candidates.update({_candidate_id: _candidate_name})
                    _state_race_data.candidates.append(_candidate_name)              
                self.races[race_id] = _state_race_data
                self.version_no.races.append(_state_race_data)
            # self.county_data.append(c)
        self.version_no.county = self.counties
        # self.version_no.races.append()
        # print([x for x in self.races.values()])
        return self
    
    def _setup_statewide_data(self):
        _offices = {}
        _candidates = {}
        for office in self._get_statewide_data():
            office_summary = self.models.StatewideOfficeSummary(
                office_id=office['OID'],
                name=office['ON'],
                version_id=self.version_no.version_id,
            )
            for x in office['C']:
                _office_data = next((x for x in self.version_no.races if x.race_id == office['OID']), None)
                if _office_data:
                    for _candidate_data in _office_data.candidates:
                        if _candidate_data.full_name == x['N']:
                            if _candidate_data.candidate_id not in _candidates:
                                _candidate = self.models.StatewideCandidateSummary(
                                        name=x['N'],
                                        party=x['P'],
                                        color=x['C'],
                                        total_votes=x['T'],
                                        ballot_order=x['O'],
                                        office_id=office['OID'],
                                        office=_office_data.office
                                )
                            else:
                                _candidate = _candidates[_candidate_data.candidate_id]
                            _candidate.county_results = _candidate_data.county_results
                            _candidates[_candidate_data.candidate_id] = _candidate
                            office_summary.candidates.append(_candidate)
            office_summary.check_for_winner()
            _offices[office_summary.office_id] = office_summary
            # for candidate in office_summary.candidates:
            #     for county in self.counties:
            #         for each_race in county.races:
            #             office_summary.race_data = each_race
            #             for each_candidate in each_race.candidates:
            #                 if each_candidate.full_name == candidate.name:
            #                     # candidate.candidate_id = each_candidate.id
            #                     candidate.candidate_data.append(each_candidate)
            # self.statewide_data = offices.values()
        self.version_no.statewide = _offices
        return self


@dataclass
class ElectionResultTicker(FileTickerFuncs):
    
    
    def _update_data(self):
        self.get_newest_version()
        sleep(5)
        return self
    
    
    # def initial_setup(self):
    #     self._get_newest_version()
    #     self._setup_county_data()
    #     self._setup_statewide_data()
    #     SQLModel.metadata.create_all(bind=self.engine)
    #     # self.logger.warning("func:update_database ENABLED")
    #     with Session(self.engine) as session:
    #         try:
    #             # First add version number
    #             session.add(self.version_no)

    #             # Cache to track what we've already added
    #             processed_races = set()
    #             processed_candidates = set()
    #             processed_counties = set()

    #             # Process each county
    #             for county in self.county_data:
    #                 if county.name not in processed_counties:
    #                     # Add county summary first
    #                     if county.summary:
    #                         session.add(county.summary)

    #                     # Process races
    #                     for race in county.races:
    #                         if race.race_id not in processed_races:
    #                             session.add(race)
    #                             processed_races.add(race.race_id)

    #                             # Process candidates for this race
    #                             for candidate in race.candidates:
    #                                 if candidate.candidate_id not in processed_candidates:
    #                                     session.add(candidate)
    #                                     processed_candidates.add(candidate.candidate_id)

    #                                     # Add candidate results
    #                                     for result in candidate.county_results:
    #                                         session.add(result)

    #                     # Add the county after its relationships
    #                     session.add(county)
    #                     processed_counties.add(county.name)
    #             # Commit everything at once at the end
    #             session.commit()
    #         except Exception as e:
    #             session.rollback()
    #             print(f"Error during database update: {e}")
    #             raise

    #     # self.logger.info("Database updated")
    # def refresh_data(self):
    #     self._get_newest_version()
    #     self._get_county_data()
    #     self._get_statewide_data()
    #     with Session(self.engine) as session:
    #         session.merge(self.version_no)
    #         for county in self.county_data:
    #             _existing_county = session.exec(select(validators.County).where(validators.County.name == county.name)).first()
    #             _existing_county.summary = county.summary

    #             for race in county.races:
    #                 _existing_race = session.exec(select(validators.RaceDetails).where(validators.RaceDetails.id)).first()
    #                 for candidate in race.candidates:
    #                     _existing_candidate = session.exec(select(validators.Candidate).where(validators.Candidate.id == candidate.id)).first()
    #                     _existing_candidate.county_name.append(_existing_county)
    #                     for result in candidate.county_results:
    #                         _existing_candidate.county_results.append(result)
    #                         session.add(_existing_candidate)
    #                     session.add(_existing_candidate)
    #                 session.add(_existing_race)
    #             session.add(_existing_county)
    #         session.commit()

    #         for office in self.statewide_data:
    #             _existing_office = session.exec(select(validators.StatewideOfficeSummary).where(validators.StatewideOfficeSummary.id == office.id)).first()
    #             for candidate in office.candidates:
    #                 _existing_candidate = session.exec(select(validators.StatewideCandidateSummary).where(validators.StatewideCandidateSummary.id == candidate.id)).first()
    #                 _existing_candidate.office_id = _existing_office.id
    #                 _existing_candidate.version_id = _existing_office.version_id
    #                 _existing_candidate.candidate_data = candidate.candidate_data
    #                 session.add(_existing_candidate)
    #             session.add(_existing_office)
    #         session.commit()

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