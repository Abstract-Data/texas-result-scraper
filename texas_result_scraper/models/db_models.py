from typing import Callable, Optional
from sqlmodel import Relationship, Field as SQLModelField, SQLModel
from ..models import bases as base  # Preferred



class CandidateRaceLink(SQLModel, table=True):
    candidate_id: str = SQLModelField(foreign_key='candidatenamebase.full_name', primary_key=True)
    race_id: int = SQLModelField(foreign_key="racedetailsbase.id", primary_key=True)

class CandidateCountyLink(SQLModel, table=True):
    county_id: str = SQLModelField(foreign_key='countybase.name', primary_key=True)
    candidate_id: int = SQLModelField(foreign_key='candidatenamebase.id', primary_key=True)

class CandidateCountyResultsLink(SQLModel, table=True):
    candidate_id: int = SQLModelField(foreign_key='candidatenamebase.id', primary_key=True)
    county_results_id: int = SQLModelField(foreign_key='candidatecountyresultsbase.id', primary_key=True)

class RaceCountyLink(SQLModel, table=True):
    county_id: str = SQLModelField(foreign_key='countybase.name', primary_key=True)
    race_id: int = SQLModelField(foreign_key="racedetailsbase.id", primary_key=True)


class StatewideRaceCountyLink(SQLModel, table=True):
    statewide_office_id: int = SQLModelField(foreign_key='statewideofficesummarybase.id', primary_key=True)
    race_id: int = SQLModelField(foreign_key="racedetailsbase.id", primary_key=True)


class StatewideCanadidateRaceLink(SQLModel, table=True):
    candidate_id: str = SQLModelField(foreign_key='candidatenamebase.full_name', primary_key=True)
    statewide_candidate_id: str = SQLModelField(foreign_key='statewidecandidatesummarybase.name', primary_key=True)
    

class ResultVersionNumberDB(base.ResultVersionNumberBase):
    statewide: list["StatewideOfficeSummaryDB"] = Relationship(back_populates="version_number")
    county: list["CountyDB"] = Relationship(back_populates="version_number")

    
class CandidateNameDB(base.CandidateNameBase):
    county_name: list["CountyDB"] = Relationship(back_populates="candidates")
    county_results: list["CandidateCountyResultsDB"] = Relationship(back_populates="candidate")
    race: "CountyRaceDetailsDB" = Relationship(back_populates="candidates")
    office: Optional["StatewideCandidateSummaryDB"] = Relationship(back_populates="candidate_data")



class CandidateCountyResultsDB(base.CandidateCountyResultsBase):
    candidate_result_id: Optional[int] = SQLModelField(default=None, primary_key=True)
    candidate: Optional[base.CandidateNameBase] = SQLModelField(default=None)
    candidate: CandidateNameDB = Relationship(back_populates="county_results")

class RaceDetailsDB(base.RaceDetailsBase):
    pass
    
class CountyRaceDetailsDB(base.CountyRaceDetailsBase):
    candidates: list[CandidateCountyResultsDB] = Relationship(back_populates="race")
    counties: list["CountyDB"] = Relationship(back_populates="races")
    office_summary: "StatewideOfficeSummaryDB" = Relationship(back_populates="race_data")

    
class CountySummaryDB(base.CountySummaryBase):
    county: "CountyDB" = Relationship(back_populates="summary")

    
class CountyDB(base.CountyBase):
    version_id: Optional[int] = SQLModelField(default=None, foreign_key='resultversionnumber.version_id')
    races: list[CountyRaceDetailsDB] = Relationship(back_populates="counties")
    summary: CountySummaryDB = Relationship(back_populates="county")
    version_number: ResultVersionNumberDB = Relationship(back_populates="county")
    


class StatewideCandidateSummaryDB(base.StatewideCandidateSummaryBase):
    office: "StatewideOfficeSummaryDB" = Relationship(back_populates="candidates")
    candidate_data: list[CandidateNameDB] = Relationship(back_populates="office")
    

class StatewideOfficeSummaryDB(base.StatewideOfficeSummaryBase):
    candidates: list[StatewideCandidateSummaryDB] = Relationship(back_populates="office")
    race_data: CountyRaceDetailsDB = Relationship(back_populates="office_summary")
    version_number: ResultVersionNumberDB = Relationship(back_populates="statewide")