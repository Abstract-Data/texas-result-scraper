from pathlib import Path
from typing import List, ForwardRef
import json

from pydantic.dataclasses import dataclass as pydantic_dataclass
from sqlmodel import Field as SQLModelField

from .models.public_models import ResultVersionNumberPublic
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
    data: ResultVersionNumberPublic = None
    exclude: set = SQLModelField(default=EXCLUDE)
    
    def __post_init__(self):
        self.ticker.create_file()


    def github_flat_file(self):
        ticker = self.ticker
        ticker.pull_data()
        ticker.create_models()
        self.data = ticker.version_no
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
            
            if isinstance(value, ResultVersionNumberPublic):
                result[field_name] = f"\n{indent}{value.debug_dump(depth + 1, seen)}"
            elif isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, ResultVersionNumberPublic):
                        items.append(item.debug_dump(depth + 1, seen))
                    else:
                        items.append(str(item))
                result[field_name] = f"\n{indent}" + f"\n{indent}".join(items)
            else:
                result[field_name] = str(value)
                
        return f"{self.data.__class__.__name__}: {json.dumps(result, indent=2)}"
    
    def write(self):
        with open(
            Path(__file__).parent / 'data'/ f'tx-{self.ticker.election_id}-{self.ticker.version_no.version_id}.json',
            'w') as f:
            f.write(
                self.data.model_dump_json(exclude_none=True)
                )