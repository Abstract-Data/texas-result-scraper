from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import Field as SQLModelField
import models.bases as base


class ResultVersionNumberPublic(base.ResultVersionNumberBase):
    statewide: dict[int, StatewideOfficeSummaryPublic] = SQLModelField(default_factory=dict)
    county: dict[str, CountyPublic] = SQLModelField(default_factory=dict)
    races: list[RaceDetailsPublic] = SQLModelField(default_factory=list)
    updated_at: str = SQLModelField(default=datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"))


class CandidateNamePublic(base.CandidateNameBase):
    county_results: list[CandidateCountyResultsPublic] = SQLModelField(default_factory=list)
    # race: "RaceDetailsPublic" = SQLModelField(default=None)
    # office: Optional["StatewideCandidateSummaryPublic"] = SQLModelField(default=None)
    


class CandidateCountyResultsPublic(base.CandidateCountyResultsBase):
    pass
    

class RaceDetailsPublic(base.RaceDetailsBase):
    candidates: list[CandidateNamePublic] = SQLModelField(default_factory=list)
    counties: list[CountyRaceDetailsPublic] = SQLModelField(default_factory=list)

class CountyRaceDetailsPublic(base.CountyRaceDetailsBase):
    # candidates: list[CandidateCountyResultsPublic] = SQLModelField(default_factory=list)
    office_summary: Optional[StatewideOfficeSummaryPublic] = None
    # TODO: Add winner data by county as dict, result
    

class CountySummaryPublic(base.CountySummaryBase):
    pass
    # county: Optional[CountyPublic] = SQLModelField(default=None)
    

class CountyPublic(base.CountyBase):
    # races: list[RaceDetailsPublic] = SQLModelField(default_factory=list)
    # candidates: list[CandidateNamePublic] = SQLModelField(default_factory=list)
    summary: Optional[CountySummaryPublic] = SQLModelField(default=None)
    version_number: int

class StatewideCandidateSummaryPublic(base.StatewideCandidateSummaryBase):
    office: str = SQLModelField(default=None)
    county_results: list[CandidateCountyResultsPublic] = SQLModelField(default_factory=list)
    

class StatewideOfficeSummaryPublic(base.StatewideOfficeSummaryBase):
    candidates: list[StatewideCandidateSummaryPublic] = SQLModelField(default_factory=list)
    race_data: Optional[CountyRaceDetailsPublic] = None
    version_number: Optional[ResultVersionNumberPublic] = None
    
    
