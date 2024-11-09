
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
from datetime import datetime
from pydantic import model_validator, ConfigDict, field_validator, BaseModel, validator, root_validator
from pydantic_extra_types.color import Color
from typing import  Optional, Annotated,  ClassVar
from pathlib import Path
import csv
from nameparser import HumanName
import texas_result_scraper.result_funcs as funcs
import hashlib


# TODO: Fix Candidate details so updates can be attached to each one, probably using a link model.

ENDORSEMENT_FILE = None

def read_endorsements(file_path: Path = ENDORSEMENT_FILE) -> list | None:
    if not file_path:
        return
    # Read first row is header keys, each row after is values
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)
        return [dict(zip(headers, row)) for row in reader]


class TimestampMixin(SQLModel):
    """Base mixin for timestamps"""
    created_at: datetime = SQLModelField(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text('CURRENT_TIMESTAMP'),
            nullable=False
        )
    )

    updated_at: datetime = SQLModelField(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text('CURRENT_TIMESTAMP'),
            onupdate=text('CURRENT_TIMESTAMP'),
            nullable=False
        )
    )


class ElectionResultValidator(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        str_to_upper=True,
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


class ResultVersionNumberBase(ElectionResultValidator):
    id: int = SQLModelField(alias='___versionNo', primary_key=True)
    election_id: int = SQLModelField(alias='___electionId')
    election_date: str = SQLModelField(alias='elecDate')
    # statewide: list["StatewideOfficeSummary"] = Relationship(back_populates='version_number')
    # county: list["County"] = Relationship(back_populates='version_number')


class ResultVersionNumber(ResultVersionNumberBase, table=True):
    statewide: list["StatewideOfficeSummary"] = Relationship(back_populates='version_number')
    county: list["County"] = Relationship(back_populates='version_number')
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )


class CandidateRaceLink(SQLModel, table=True):
    candidate_id: str = SQLModelField(foreign_key='candidatename.full_name', primary_key=True)
    race_id: int = SQLModelField(foreign_key="racedetails.id", primary_key=True)

class CandidateCountyLink(SQLModel, table=True):
    county_id: str = SQLModelField(foreign_key='county.name', primary_key=True)
    candidate_id: int = SQLModelField(foreign_key='candidatename.id', primary_key=True)

class CandidateCountyResultsLink(SQLModel, table=True):
    candidate_id: int = SQLModelField(foreign_key='candidatename.id', primary_key=True)
    county_results_id: int = SQLModelField(foreign_key='candidatecountyresults.id', primary_key=True)

class RaceCountyLink(SQLModel, table=True):
    county_id: str = SQLModelField(foreign_key='county.name', primary_key=True)
    race_id: int = SQLModelField(foreign_key="racedetails.id", primary_key=True)


class StatewideRaceCountyLink(SQLModel, table=True):
    statewide_office_id: int = SQLModelField(foreign_key='statewideofficesummary.id', primary_key=True)
    race_id: int = SQLModelField(foreign_key="racedetails.id", primary_key=True)


class StatewideCanadidateRaceLink(SQLModel, table=True):
    candidate_id: str = SQLModelField(foreign_key='candidatename.full_name', primary_key=True)
    statewide_candidate_id: str = SQLModelField(foreign_key='statewidecandidatesummary.name', primary_key=True)


class CandidateEndorsements(ElectionResultValidator):
    id: Optional[int] = None
    candidate_office_id: Optional[int] = None
    district: Annotated[
        str,
        SQLModelField(
            alias='District Type',
            description="Type of district"
        )
    ]
    district_number: Annotated[
        int,
        SQLModelField(
            alias='District Number',
            description="District number"
        )
    ]
    paxton: Annotated[
        Optional[bool],
        SQLModelField(
            alias='Paxton Endorsed',
            description="Endorsed by Texas Attorney General Ken Paxton"
        )
    ] = None
    candidate_first_name: Annotated[
        str,
        SQLModelField(
            alias='Candidate First Name',
            description="First name of candidate"
        )
    ]
    candidate_last_name: Annotated[
        str,
        SQLModelField(
            alias='Candidate Last Name',
            description="Last name of candidate"
        )
    ]
    abbott: Annotated[
        Optional[bool],
        SQLModelField(
            alias='Abbott Endorsed',
            description="Endorsed by Texas Governor Greg Abbott"
        )
    ] = None
    perry: Annotated[
        Optional[bool],
        SQLModelField(
            alias='Rick Perry Endorsed',
            description="Endorsed by former Texas Governor Rick Perry"
        )
    ] = None
    miller: Annotated[
        Optional[bool],
        SQLModelField(
            alias='Sid Miller Endorsed',
            description="Endorsed by Texas Agriculture Commissioner Sid Miller"
        )
    ] = None
    patrick: Annotated[
        Optional[bool],
        SQLModelField(
            alias='Dan Patrick Endorsed',
            description="Endorsed by Texas Lieutenant Governor Dan Patrick"
        )
    ] = None

    # vote_percent: Optional[float] = None
    # win_or_made_runoff: Optional[bool] = None

    @model_validator(mode='before')
    def strip_blank_strings(cls, values):
        for k, v in values.items():
            if v == "":
                values[k] = None
        return values

    @model_validator(mode='after')
    def generate_endorsement_id(self):
        # create a string representation of the model
        _endorsee_vars = [self.candidate_first_name, self.candidate_last_name, self.district, self.district_number]
        model_string = str("".join([str(var).strip() for var in _endorsee_vars]))

        # hash the string
        endorsement_id = hashlib.sha256(model_string.encode()).hexdigest()

        # add the consistent hash to the model
        self.id = int(endorsement_id, 16) % (10 ** 8)

        return self


# ENDORSEMENT_DICT = read_endorsements()
# ENDORSEMENTS = [CandidateEndorsements(**endorsement) for endorsement in ENDORSEMENT_DICT] if ENDORSEMENT_DICT else []
class CandidateNameBase(ElectionResultValidator):
    id: int = SQLModelField(primary_key=True)
    full_name: str = SQLModelField(..., unique=True)
    first_name: Optional[str] = SQLModelField(default=None)
    last_name: Optional[str] = SQLModelField(default=None)
    incumbent: Optional[bool] = SQLModelField(default=None)
    party: str
    # endorsements: Optional[CandidateEndorsements] = None
    # race: "RaceDetails" = Relationship(back_populates='candidates', link_model=CandidateRaceLink)
    # office: "StatewideCandidateSummary" = Relationship(
    #     back_populates='candidate_data',
    #     link_model=StatewideCanadidateRaceLink)

    @model_validator(mode='before')
    @classmethod
    def set_incumbent(cls, values):
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
        if _name := values.get('full_name'):
            parsed_name = HumanName(_name)
            values['first_name'] = parsed_name.first
            values['last_name'] = parsed_name.last
        return values


class CandidateName(CandidateNameBase, table=True):
    county_name: list["County"] = Relationship(back_populates='candidates', link_model=CandidateCountyLink)
    county_results: list["CandidateCountyResults"] = Relationship(back_populates='candidate', link_model=CandidateCountyResultsLink)
    race: list["RaceDetails"] = Relationship(back_populates='candidates', link_model=CandidateRaceLink)
    office: "StatewideCandidateSummary" = Relationship(
        back_populates='candidate_data',
        link_model=StatewideCanadidateRaceLink)
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )

class CandidateCountyResultsBase(ElectionResultValidator):
    id: Optional[int] = SQLModelField(default=None, primary_key=True)
    # candidate_id: int = SQLModelField(foreign_key='candidatename.id')
    early_votes: int
    total_votes: int
    percent: float
    color: Color = SQLModelField(sa_type=String)
    ballot_order: int

    @field_validator('color')
    def validate_color(cls, v: Color):
        return v.as_hex()

class CandidateCountyResults(CandidateCountyResultsBase, table=True):
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )
    candidate: "CandidateName" = Relationship(back_populates='county_results', link_model=CandidateCountyResultsLink)



class RaceDetailsBase(ElectionResultValidator):
    id: int = SQLModelField(alias='OID', primary_key=True)
    office: str
    office_type: Optional[str] = SQLModelField(default=None)
    office_district: Optional[str] = SQLModelField(default=None)
    total_votes: int = SQLModelField(alias='T')
    ballot_order: int = SQLModelField(alias='O')
    precincts_reporting: int = SQLModelField(alias='PR')
    registered_voters: int = SQLModelField(alias='OTRV')
    total_precincts: int = SQLModelField(alias='TPR')
    # candidates: list["Candidate"] = Relationship(back_populates='race', link_model=CandidateRaceLink)
    # counties: list["County"] = Relationship(back_populates='races', link_model=RaceCountyLink)
    # office_summary: Optional["StatewideOfficeSummary"] = Relationship(back_populates="race_data", link_model=StatewideRaceCountyLink)

    _set_office_type = model_validator(mode='before')(funcs.set_office_type)
    # _set_district_number = model_validator(mode='before')(funcs.set_district_number)

class RaceDetails(RaceDetailsBase, table=True):
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )
    candidates: list["CandidateName"] = Relationship(back_populates='race', link_model=CandidateRaceLink)
    counties: list["County"] = Relationship(back_populates='races', link_model=RaceCountyLink)
    office_summary: Optional["StatewideOfficeSummary"] = Relationship(back_populates="race_data", link_model=StatewideRaceCountyLink)


class CountySummaryBase(ElectionResultValidator):
    id: Optional[int] = SQLModelField(default=None, primary_key=True)
    precincts_reporting: int = SQLModelField(default=None, alias='PRR')
    total_precincts: int = SQLModelField(default=None, alias='PRP')
    percent_reporting: float = SQLModelField(default=None, alias='P')
    registered_voters: int = SQLModelField(default=None, alias='RV')
    voted_counted: int = SQLModelField(default=None, alias='VC')
    turnout_percent: float = SQLModelField(default=None, alias='VT')
    poll_loc: int = SQLModelField(default=None, alias='NPL')
    poll_loc_reporting: int = SQLModelField(default=None, alias='PLR')
    poll_loc_percent: float = SQLModelField(default=None, alias='PLP')
    county_name: Optional[str] = SQLModelField(foreign_key='county.name')
    # counties: "County" = Relationship(back_populates='summary')

class CountySummary(CountySummaryBase, table=True):
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )
    counties: "County" = Relationship(back_populates='summary')

class CountyBase(ElectionResultValidator):
    name: str = SQLModelField(alias='N', primary_key=True)
    registered_voters: int = SQLModelField(alias='TV')
    color: Color = SQLModelField(alias='C', sa_type=String)
    version_id: Optional[int] = SQLModelField(default=None, foreign_key='resultversionnumber.id')
    # races: list["RaceDetails"] = Relationship(back_populates='counties', link_model=RaceCountyLink)
    # summary: "CountySummary" = Relationship(back_populates='counties')
    # version_number: "ResultVersionNumber" = Relationship(back_populates='county')
    @field_validator('color')
    def validate_color(cls, v: Color):
        return v.as_hex()

class County(CountyBase, table=True):
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )
    races: list["RaceDetails"] = Relationship(back_populates='counties', link_model=RaceCountyLink)
    candidates: list["CandidateName"] = Relationship(back_populates='county_name', link_model=CandidateCountyLink)
    summary: "CountySummary" = Relationship(back_populates='counties')
    version_number: "ResultVersionNumber" = Relationship(back_populates='county')


class StatewideCandidateSummaryBase(ElectionResultValidator):
    name: str = SQLModelField(primary_key=True)
    first_name: Optional[str] = SQLModelField(default=None)
    last_name: Optional[str] = SQLModelField(default=None)
    party: str = SQLModelField(alias='P')
    color: Color = SQLModelField(alias='C', sa_type=String)
    total_votes: int = SQLModelField(alias='T')
    ballot_order: int = SQLModelField(alias='O')
    # endorsement_id: Optional[int] = None
    office_id: int = SQLModelField(foreign_key='statewideofficesummary.id')
    # office: "StatewideOfficeSummary" = Relationship(back_populates='candidates')
    # candidate_data: "Candidate" = Relationship(back_populates='office', link_model=StatewideCanadidateRaceLink)

    @model_validator(mode='before')
    @classmethod
    def parse_name(cls, values):
        if _name := values['name']:
            _clean_name = _name.replace("(I)", "").strip()
            name = HumanName(_clean_name)
            values['first_name'] = name.first
            values['last_name'] = name.last
        return values
    @field_validator('color')
    def validate_color(cls, v: Color):
        return v.as_hex()


class StatewideCandidateSummary(StatewideCandidateSummaryBase, table=True):
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )
    office: "StatewideOfficeSummary" = Relationship(back_populates='candidates')
    candidate_data: "CandidateName" = Relationship(back_populates='office', link_model=StatewideCanadidateRaceLink)


class StatewideOfficeSummaryBase(ElectionResultValidator):
    id: int = SQLModelField(alias='OID', primary_key=True)
    name: str = SQLModelField(alias='ON')
    office_type: Optional[str] = None
    office_district: Optional[str] = None
    winner: Optional[str] = SQLModelField(default=None)
    winner_party: Optional[str] = SQLModelField(default=None)
    winner_margin: Optional[int] = SQLModelField(default=None)
    winner_percent: Optional[float] = SQLModelField(default=None)
    version_id: Optional[int] = SQLModelField(default=None, foreign_key='resultversionnumber.id')
    # candidates: list["StatewideCandidateSummary"] = Relationship(back_populates='office')
    # race_data: "RaceDetails" = Relationship(back_populates='office_summary', link_model=StatewideRaceCountyLink)
    # version_number: "ResultVersionNumber" = Relationship(back_populates='statewide')

    def __init__(self, **data):
        super().__init__(**data)
        self.check_for_winner()

    _set_office_type = model_validator(mode='before')(funcs.set_office_type)
    def check_for_winner(self):
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


class StatewideOfficeSummary(StatewideOfficeSummaryBase, table=True):
    created_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: Optional[datetime] = SQLModelField(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
        default=None
    )
    candidates: list["StatewideCandidateSummary"] = Relationship(back_populates='office')
    race_data: "RaceDetails" = Relationship(back_populates='office_summary', link_model=StatewideRaceCountyLink)
    version_number: "ResultVersionNumber" = Relationship(back_populates='statewide')
