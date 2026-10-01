import configparser

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

config = configparser.ConfigParser()
config.read("app.conf")

DB_HOST = config["DATABASE"]["HOST"]
DB_PORT = config["DATABASE"]["PORT"]
DB_NAME = config["DATABASE"]["NAME"]
DB_USER = config["DATABASE"]["USER"]
DB_PASSWORD = config["DATABASE"]["PASSWORD"]

DATABASE_URL = (
    f"postgresql+pg8000://"
    f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()