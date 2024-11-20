import abc
from typing import  Optional, Annotated,  ClassVar, List, TypeVar, Union, Protocol, Type, Any
from pathlib import Path
import csv
from datetime import datetime, date
import hashlib

from sqlmodel import (
    SQLModel,
    Field as SQLModelField,
    Relationship,
    JSON,
    String,
    DateTime,
    Column,
    text,
    func,
    Session,
    select
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import declared_attr
from pydantic import model_validator, ConfigDict, field_validator, BaseModel, computed_field
from pydantic_extra_types.color import Color
from nameparser import HumanName

import texas_result_scraper.funcs as funcs


T = TypeVar('T')

class RelationshipProtocol(Protocol[T]):
    def __call__(self, *args, **kwargs) -> T: ...
    
    
RelationshipOrList = Union[RelationshipProtocol[T], List[T], List[RelationshipProtocol[T]]]


class ElectionResultValidator(SQLModel, abc.ABC):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        str_to_upper=True,
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )
    
    def __repr__(cls) -> str:
        return cls.__class__.__name__
    
    def __str__(cls) -> str:
        return cls.__repr__()


class ResultVersionNumberBase(ElectionResultValidator):
    version_id: int = SQLModelField(alias='___versionNo', primary_key=True)
    election_id: int = SQLModelField(alias='___electionId')
    election_date: date = SQLModelField(alias='elecDate')
    # statewide: list[ElectionResultValidator] = SQLModelField(default_factory=list)
    # county: list[ElectionResultValidator] = SQLModelField(default_factory=list)


    
    def __repr__(cls) -> str:
        return f"{cls.__class__.__name__}({cls.election_date}-{cls.version_id})"
    
    @field_validator('election_date', mode='before')
    @classmethod
    def format_date(cls, value: str) -> datetime:
        for fmt in ['%m%d%Y', '%Y-%m-%d']:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
            
    def flatten_races(self):
        return [x.flatten() for x in self.races]
    
    def flatten_counties(self):
        return [x.summary.model_dump() for x in self.county.values()]

    def flatten_statewide(self):
        data = []
        for office in self.statewide.values():
            data.extend(office.flatten())
        return data
    

class CandidateNameBase(ElectionResultValidator):
    candidate_id: int = SQLModelField(alias='id', primary_key=True)
    full_name: Optional[str] = SQLModelField(alias='N', default=None, unique=True)
    first_name: Optional[str] = SQLModelField(default=None)
    last_name: Optional[str] = SQLModelField(default=None)
    incumbent: Optional[bool] = SQLModelField(default=None)
    party: str = SQLModelField(alias='P')
    # county_name: Optional[list[ElectionResultValidator]] = SQLModelField(default=None)
    county_results: Optional[list[ElectionResultValidator]] = SQLModelField(default_factory=list)
    # race: Optional[ElectionResultValidator] = SQLModelField(default=None)
    # office: Optional[ElectionResultValidator] = SQLModelField(default=None)

    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.full_name})[{self.party}]"
    

    @model_validator(mode='before')
    @classmethod
    def set_incumbent(cls, values):
        if isinstance(values, SQLModel):
            values = values.model_dump()
        if _name := values.get('full_name'):
            if "(I)" in _name:
                values['incumbent'] = True
            else:
                values['incumbent'] = False
        return values

    @field_validator('party')
    def validate_party(cls, value):
        if value == 'REP':
            return 'Republican'
        elif value == 'DEM':
            return 'Democrat'
        elif value == 'LIB':
            return 'Libertarian'
        elif value == 'GRE':
            return 'Green'
        elif value == 'IND':
            return 'Independent'
        elif value == 'W':
            return 'Write-In'
        else:
            return value


    @model_validator(mode='before')
    @classmethod
    def parse_name(cls, values):
        _name = values.get('full_name')
        if _name and '/' not in _name:
            parsed_name = HumanName(_name)
            values['first_name'] = parsed_name.first
            values['last_name'] = parsed_name.last
        return values
    
    
    
class CandidateCountyResultsBase(ElectionResultValidator):
    county: str = SQLModelField(...)
    early_votes: int
    total_votes: int = SQLModelField(...)
    percent: float = SQLModelField(...)
    color: Color = SQLModelField(default_factory=Color, sa_type=String)
    ballot_order: Optional[int] = SQLModelField(default=None)

    @computed_field
    @property
    def election_day_votes(self) -> int:
        return self.total_votes - self.early_votes

    # @field_validator('color')
    # def validate_color(cls, v: Color):
    #     return v.as_hex()
    

class RaceDetailsBase(ElectionResultValidator):
    race_id: int = SQLModelField(..., primary_key=True)
    office: str = SQLModelField(...)
    office_type: Optional[str] = SQLModelField(default=None)
    office_district: Optional[str] = SQLModelField(default=None)
    total_votes: int = SQLModelField(default=0)
    # ballot_order: int = SQLModelField(..., exclude=True)
    precincts_reporting: int = SQLModelField(default=0)
    registered_voters: int = SQLModelField(default=0)
    total_precincts: int = SQLModelField(default=0)
    candidates: list[ElectionResultValidator] | dict[str, ElectionResultValidator] = SQLModelField(default_factory=list)
    counties: list[ElectionResultValidator] = SQLModelField(default_factory=list)
    
    @computed_field
    @property
    def turnout_pct(self) -> float:
        self.update_counts()
        if any(value == 0 for value in [
            self.total_votes,
            self.registered_voters
        ]):
            return 0
        return round(self.total_votes / self.registered_voters, 2)
    
    @computed_field
    @property
    def precinct_reporting_pct(self) -> float:
        self.update_counts()
        if any(value == 0 for value in [
            self.precincts_reporting,
            self.total_precincts
        ]):
            return 0
        return round(self.precincts_reporting / self.total_precincts, 2)
    
    def update_counts(self):
        self.precincts_reporting = sum(x.county_precincts_reporting for x in self.counties)
        self.registered_voters = sum(x.county_registered_voters for x in self.counties)
        self.total_precincts = sum(x.county_precincts for x in self.counties)
        self.total_votes = sum(x.county_total_votes for x in self.counties)
        if any(value == 0 for value in [
            self.total_votes,
            self.total_precincts, 
            self.registered_voters,
            self.precincts_reporting
        ]):
            return self
            # raise ValueError(f"Office: {self.office} Candidate vote totals are not complete - found zero values")
        return self
    
    def flatten(self):
        race_details = {
        'office': self.office,
        'office_type': self.office_type,
        'office_district': self.office_district,
        }
        for candidate in self.candidates:
            race_details['candidate'] = candidate.full_name
            race_details['party'] = candidate.party
            for county in candidate.county_results:
                race_details['county'] = county.county
                race_details['early_votes'] = county.early_votes
                race_details['election_day_votes'] = county.election_day_votes
                race_details['total_votes'] = county.total_votes
                race_details['percent_votes'] = county.percent
        return race_details
    
    _set_office_type = model_validator(mode='before')(funcs.set_office_type)

class CountyRaceDetailsBase(ElectionResultValidator):
    county: str = SQLModelField(..., primary_key=True)
    race_id: int = SQLModelField(..., primary_key=True)
    # office: str = SQLModelField(...)
    # office_type: Optional[str] = SQLModelField(default=None)
    # office_district: Optional[str] = SQLModelField(default=None)
    county_total_votes: int = SQLModelField(default=0)
    county_ballot_order: int = SQLModelField(...)
    county_precincts_reporting: int = SQLModelField(default=0)
    county_registered_voters: int = SQLModelField(default=0)
    county_precincts: int = SQLModelField(default=0)
    # candidates: list[ElectionResultValidator] | dict[str, ElectionResultValidator] = SQLModelField(default=None)
    # counties: list[ElectionResultValidator] = SQLModelField(default_factory=list)
    # office_summary: Optional[ElectionResultValidator] = SQLModelField(default=None)
    
    def __repr__(cls) -> str:
        return f"{cls.__class__.__name__}({cls.office})"
    
    @computed_field
    @property
    def county_turnout_pct(self) -> float:
        if any(value == 0 for value in [
            self.county_total_votes,
            self.county_registered_voters
        ]):
            return 0
        return round(self.county_total_votes / self.county_registered_voters, 2)
    
    @computed_field
    @property
    def county_precinct_pct(self) -> float:
        if any(value == 0 for value in [
            self.county_precincts_reporting,
            self.county_precincts
        ]):
            return 0
        return round(self.county_precincts_reporting / self.county_precincts, 2)

    
    
    
class CountySummaryBase(ElectionResultValidator):
    # id: Optional[int] = SQLModelField(default=None, primary_key=True)
    county_name: Optional[str] = SQLModelField(primary_key=True)
    precincts_reporting: int = SQLModelField(default=None, alias='PRR')
    total_precincts: int = SQLModelField(default=None, alias='PRP')
    percent_reporting: float = SQLModelField(default=None, alias='P')
    registered_voters: int = SQLModelField(default=None, alias='RV')
    voted_counted: int = SQLModelField(default=None, alias='VC')
    turnout_percent: float = SQLModelField(default=None, alias='VT')
    poll_locations: int = SQLModelField(default=None, alias='NPL')
    poll_locations_reporting: int = SQLModelField(default=None, alias='PLR')
    poll_locations_percent: float = SQLModelField(default=None, alias='PLP')
    # county: Optional[ElectionResultValidator] = SQLModelField(default=None)
    
    
    
class CountyBase(ElectionResultValidator):
    name: str = SQLModelField(alias='N', primary_key=True)
    # registered_voters: int = SQLModelField(alias='TV')
    color: Color = SQLModelField(sa_type=String, default_factory=Color)
    summary: Optional[ElectionResultValidator] = SQLModelField(default=None)

    
    
    def __repr__(cls) -> str:
        return f"{cls.__class__.__name__}({cls.name.title()} county)"

    
    
    
class StatewideCandidateSummaryBase(ElectionResultValidator):
    name: str = SQLModelField(alias='N', primary_key=True)
    first_name: Optional[str] = SQLModelField(default=None)
    last_name: Optional[str] = SQLModelField(default=None)
    incumbent: Optional[bool] = SQLModelField(default=None)
    party: str = SQLModelField(...)
    color: Color = SQLModelField(..., sa_type=String, default_factory=Color)
    total_votes: int = SQLModelField(...)
    ballot_order: int = SQLModelField(...)
    # endorsement_id: Optional[int] = None
    office_id: int = SQLModelField(foreign_key='statewideofficesummary.id')
    office: Optional[ElectionResultValidator] = SQLModelField(default=None)
    # candidate_data: list[ElectionResultValidator] = SQLModelField(default_factory=list)
    
    @model_validator(mode='before')
    @classmethod
    def set_incumbent(cls, values):
        if isinstance(values, SQLModel):
            values = values.model_dump()
        if _name := values.get('name'):
            if "(I)" in _name:
                values['incumbent'] = True
            else:
                values['incumbent'] = False
        return values
    
    @model_validator(mode='before')
    @classmethod
    def parse_name(cls, values):
        if _name := values.get('name'):
            _clean_name = _name.replace("(I)", "").strip()
            if '/' not in _clean_name:
                name = HumanName(_clean_name)
                values['first_name'] = name.first
                values['last_name'] = name.last
            else:
                values['name'] = _clean_name
        return values

    
    
    

class StatewideOfficeSummaryBase(ElectionResultValidator):
    office_id: int = SQLModelField(alias='OID', primary_key=True)
    name: str = SQLModelField(alias='ON')
    office_type: Optional[str] = None
    office_district: Optional[str] = None
    winner: Optional[str] = SQLModelField(default=None)
    winner_party: Optional[str] = SQLModelField(default=None)
    winner_margin: Optional[int] = SQLModelField(default=None)
    winner_percent: Optional[float] = SQLModelField(default=None)
    version_id: Optional[int] = SQLModelField(default=None, foreign_key='resultversionnumber.version_id')
    candidates: list[ElectionResultValidator] = SQLModelField(default_factory=list)
    # race_data: Optional[ElectionResultValidator] = SQLModelField(default=None)


    def __init__(self, **data):
        super().__init__(**data)

    _set_office_type = model_validator(mode='before')(funcs.set_office_type)
    def check_for_winner(self):
        if self.candidates:
            _vote_totals = sorted([x.total_votes for x in self.candidates])
            _winner = next(x for x in self.candidates if x.total_votes == max(x.total_votes for x in self.candidates))
            self.winner = _winner.name
            self.winner_party = _winner.party
            if len(_vote_totals) > 1:
                if sum(_vote_totals) != 0:
                    self.winner_margin = _vote_totals[-1] - _vote_totals[-2]
                    self.winner_percent = _winner.total_votes / sum(x.total_votes for x in self.candidates)
            else:
                self.winner_margin = 0
                self.winner_percent = 100
        return self

    def flatten(self):
        """Convert office data to hashable format for deduplication"""
        all_office_data = set()

        base_data = {
            'version': self.version_id,
            'office': self.name,
            'office_type': self.office_type,
            'office_district': self.office_district,
            'winner': self.winner,
            'winner_party': self.winner_party,
            'winner_margin': self.winner_margin,
            'winner_percent': self.winner_percent,
        }

        for candidate in self.candidates:
            for county in candidate.county_results:
                # Create new dict for each county result
                row_data = {
                    **base_data,
                    'candidate': candidate.name,
                    'party': candidate.party,
                    'county': county.county,
                    'early_votes': county.early_votes,
                    'election_day_votes': county.election_day_votes,
                    'total_votes': county.total_votes,
                    'percent': county.percent
                }
                # Convert to hashable tuple of key-value pairs
                hashable_data = frozenset(row_data.items())
                all_office_data.add(hashable_data)

        # Convert back to list of dicts
        return [dict(data) for data in all_office_data]