from pathlib import Path
from sqlmodel import create_engine, Session
import sqlite3


""" LOCAL SQL LITE DATABASE CONNECTION """
conn = sqlite3.connect(f'{Path(__file__).parent / "p2024_results.db"}')

engine = create_engine(f'sqlite:///{Path(__file__).parent / "p2024_results.db"}')

psql_engine = create_engine(f"postgresql://postgres:tbone1987@localhost:5432/g2024")
SessionLocal = Session(bind=engine)