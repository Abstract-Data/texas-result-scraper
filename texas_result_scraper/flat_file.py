from pathlib import Path
from typing import List, ForwardRef
import json

from pydantic.dataclasses import dataclass as pydantic_dataclass
from sqlmodel import Field as SQLModelField

import models.public_models as public
from .scraper import ElectionResultTicker


EXCLUDE = {
        "county_name",
        "county_results", 
        "race",
        "office",
        "version_number"
        }


@pydantic_dataclass(config={"arbitrary_types_allowed": True})
class GitHubFile:
    ticker: ElectionResultTicker
    data: public.ResultVersionNumberPublic = None
    exclude: set = SQLModelField(default=EXCLUDE)
    file_name: str = SQLModelField(default=None)
    
    def __post_init__(self):
        self.ticker.create_file()


    def github_flat_file(self):
        ticker = self.ticker
        ticker.pull_data()
        ticker.create_models()
        self.data = ticker.version_no
        self.file_name = f'tx-{self.ticker.election_id}-{self.ticker.version_no.version_id}.json'
        return self
    
    def dump_model(self):
        return self.data.model_dump()
    
    def debug_dump(self, depth=0, seen=None):
        if seen is None:
            seen = set()
            
        # Check for circular reference
        if id(self.data) in seen:
            return f"<Circular ref to {self.data.__class__.__name__}>"
            
        seen.add(id(self.data))
        
        # Get all fields
        result = {}
        indent = "  " * depth
        
        for field_name, field in self.data.__fields__.items():
            value = getattr(self.data, field_name)
            
            if isinstance(value, public.ResultVersionNumberPublic):
                result[field_name] = f"\n{indent}{value.debug_dump(depth + 1, seen)}"
            elif isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, public.ResultVersionNumberPublic):
                        items.append(item.debug_dump(depth + 1, seen))
                    else:
                        items.append(str(item))
                result[field_name] = f"\n{indent}" + f"\n{indent}".join(items)
            else:
                result[field_name] = str(value)
                
        return f"{self.data.__class__.__name__}: {json.dumps(result, indent=2)}"
    
    def write(self) -> None:
        with open(
            Path(__file__).parent / 'data'/ self.file_name,
            'w') as f:
            f.write(
                self.data.model_dump_json(exclude_none=True)
                )
            
    def read(self) -> public.ResultVersionNumberPublic:
        _path = Path(__file__).parent / 'data'/ self.file_name
        with open(_path, 'r') as f:
            data = json.loads(f.read())
            output = {
                'version_id': data.pop('version_id'),
                'election_id': data.pop('election_id'),
                'election_date': data.pop('election_date'),
                'statewide': {
                    k: public.StatewideOfficeSummaryPublic(
                        candidates=[
                            public.StatewideCandidateSummaryPublic(
                                county_results=[
                                    public.CandidateCountyResultsPublic(**result) for result in y.pop('county_results')
                                ],
                                **y
                            ) for y in v.pop('candidates')],
                        **v
                        ) for k, v in data['statewide'].items()},
                'county': {
                    k: public.CountyPublic(
                        summary=public.CountySummaryPublic(**v.pop('summary')),
                        **v
                    ) for k, v in data['county'].items()},
                'races': [
                    public.RaceDetailsPublic(
                        candidates=[
                            public.CandidateNamePublic.construct(
                                county_results=[
                                    public.CandidateCountyResultsPublic(
                                        **result
                                    ) for result in c.pop('county_results')
                                ],
                                **c) for c in r.pop('candidates')],
                        counties=[public.CountyRaceDetailsPublic(**c) for c in r.pop('counties')],
                        **r
                    ) for r in data['races']],
            }
            return public.ResultVersionNumberPublic(**output)
    
    