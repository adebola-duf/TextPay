import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine

load_dotenv(".env")
db_url = os.getenv("DB_URL")

engine = create_engine(db_url, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
