from typing import Tuple
import abc
from dataclasses import dataclass

from sqlmodel import SQLModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from texas_result_scraper.models import db_models
from texas_result_scraper.models import public_models


@pydantic_dataclass
class ModelTypes:
    db_model: SQLModel
    public_model: SQLModel

@dataclass
class ModelGroup:
    ResultVersionNumber: SQLModel
    CandidateName: SQLModel
    CandidateCountyResults: SQLModel
    RaceDetails: SQLModel
    CountyRaceDetails: SQLModel
    CountySummary: SQLModel
    County: SQLModel
    StatewideCandidateSummary: SQLModel
    StatewideOfficeSummary: SQLModel
    ReturnTypes: Tuple[SQLModel, SQLModel]
    
    def __repr__(cls) -> str:
        return cls.__name__
    
    def __str__(cls) -> str:
        return cls.__repr__()
    
    
@pydantic_dataclass
class DBModels(ModelGroup):
    ResultVersionNumber = db_models.ResultVersionNumberDB
    CandidateName = db_models.CandidateNameDB
    CandidateCountyResults = db_models.CandidateCountyResultsDB
    RaceDetails = db_models.RaceDetailsDB
    CountyRaceDetails = db_models.CountyRaceDetailsDB
    CountySummary = db_models.CountySummaryDB
    County = db_models.CountyDB
    StatewideCandidateSummary = db_models.StatewideCandidateSummaryDB
    StatewideOfficeSummary = db_models.StatewideOfficeSummaryDB
    ReturnTypes = (
        db_models.ResultVersionNumberDB, 
        db_models.CandidateNameDB, 
        db_models.CandidateCountyResultsDB, 
        db_models.CountyRaceDetailsDB, 
        db_models.CountySummaryDB, 
        db_models.CountyDB, 
        db_models.StatewideCandidateSummaryDB, 
        db_models.StatewideOfficeSummaryDB
        )


@pydantic_dataclass
class FileModels(ModelGroup):
    ResultVersionNumber = public_models.ResultVersionNumberPublic
    CandidateName = public_models.CandidateNamePublic
    CandidateCountyResults = public_models.CandidateCountyResultsPublic
    RaceDetails = public_models.RaceDetailsPublic
    CountyRaceDetails = public_models.CountyRaceDetailsPublic
    CountySummary = public_models.CountySummaryPublic
    County = public_models.CountyPublic
    StatewideCandidateSummary = public_models.StatewideCandidateSummaryPublic
    StatewideOfficeSummary = public_models.StatewideOfficeSummaryPublic
    ReturnTypes = (
        public_models.ResultVersionNumberPublic, 
        public_models.CandidateNamePublic, 
        public_models.CandidateCountyResultsPublic, 
        public_models.RaceDetailsPublic, 
        public_models.CountyRaceDetailsPublic,
        public_models.CountySummaryPublic, 
        public_models.CountyPublic, 
        public_models.StatewideCandidateSummaryPublic, 
        public_models.StatewideOfficeSummaryPublic
        )