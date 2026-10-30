from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

class Base(DeclarativeBase): pass

def make_engine(url: str = settings.database_url):
    if url.startswith("sqlite") and url != "sqlite:///:memory:":
        Path(url.split("///", 1)[1]).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def initialize_database():
    """Create missing tables and add new nullable analysis columns without deleting rows."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        existing = {column["name"] for column in inspect(connection).get_columns("reports")}
        additions = {"transportation_mode": "VARCHAR(60)", "suggested_category": "VARCHAR(60)", "category_source": "VARCHAR(30)", "analysis_source": "VARCHAR(40)", "priority_factors": "JSON"}
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE reports ADD COLUMN {name} {sql_type}"))
    # Give legacy rows a current, structured rules-based explanation. Keep their category and description.
    from .models import Report
    from .services.ai_service import analyze
    db = SessionLocal()
    try:
        for report in db.query(Report).all():
            if report.priority_factors is None:
                category, summary, score, level, explanation, factors, suggested = analyze(
                    report.title, report.description, report.category, report.location_name, report.transportation_mode
                )
                report.priority_score, report.priority_level = score, level
                report.priority_explanation, report.priority_factors = explanation, factors
                report.summary = report.summary or summary
                report.suggested_category = report.suggested_category or suggested
            report.category_source = report.category_source or "legacy"
            report.analysis_source = report.analysis_source or "rules"
        db.commit()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
