"""
DATABASE MODULE (database.py)
-----------------------------
Purpose:
This file sets up the SQLAlchemy database connection for the Learn & Grow application.
It dynamically supports both local SQLite and Render's PostgreSQL databases.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Fallback to local SQLite if DATABASE_URL is not provided (e.g. local dev)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./learnandgrow.db")

# Render uses 'postgres://' but SQLAlchemy 1.4+ requires 'postgresql://'
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
