"""Add 20 stable-ID synthetic Mangaluru civic reports without resetting data."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, initialize_database
from app.models import Report, StatusHistory
from app.services.ai_service import analyze
from app.services.duplicate_service import candidates

DEMO_REPORTS = [
    ("Pothole beside Hampankatta bus stop", "A deep pothole beside the bus stop makes motorcycles swerve into the next lane.", "Roads and Infrastructure", "Hampankatta", 12.8687, 74.8420, "Two-Wheeler / Motorcycle", "SUBMITTED", 2),
    ("Broken footpath tiles near Central Market", "Several loose footpath tiles create a trip hazard for people walking near the market entrance.", "Roads and Infrastructure", "Hampankatta", 12.8690, 74.8430, "Walking / Pedestrian", "UNDER_REVIEW", 5),
    ("Drain blocked after evening rain", "A blocked roadside drain beside the Bejai junction is backing up after rainfall. Water is pooling at this same junction.", "Drainage and Waterlogging", "Bejai", 12.8840, 74.8440, "Walking / Pedestrian", "ASSIGNED", 8),
    ("Blocked drain near Bejai junction", "The blocked roadside drain beside the Bejai junction is backing up after rainfall. Water is pooling at this same junction. Leaves and litter are also visible.", "Drainage and Waterlogging", "Bejai", 12.8842, 74.8442, "Multiple Modes / General Traffic", "SUBMITTED", 1),
    ("Water leaking from roadside pipe", "A steady leak is running from a roadside pipe and leaving water across the footpath.", "Water Supply", "Kankanady", 12.8705, 74.8530, "Walking / Pedestrian", "IN_PROGRESS", 12),
    ("Low water pressure in upper floors", "Residents report irregular water pressure in the morning and request an inspection of the supply.", "Water Supply", "Kadri", 12.8800, 74.8550, "Not Applicable", "UNDER_REVIEW", 4),
    ("Garbage accumulation beside apartments", "Uncollected household waste has accumulated beside the public collection point.", "Sanitation and Garbage", "Bendoor", 12.8640, 74.8500, "Not Applicable", "ASSIGNED", 10),
    ("Overflowing public bin beside apartments", "Uncollected household waste has accumulated beside the public collection point. Waste is overflowing from the public bin.", "Sanitation and Garbage", "Bendoor", 12.8642, 74.8502, "Walking / Pedestrian", "SUBMITTED", 3),
    ("Streetlight out on residential lane", "A streetlight has not worked for several nights on the lane used by people walking home.", "Street Lighting", "Falnir", 12.8720, 74.8500, "Walking / Pedestrian", "RESOLVED", 18),
    ("Traffic sign bent at road divider", "A damaged direction sign is turned away from approaching traffic and may confuse drivers.", "Transportation", "Lalbagh", 12.8820, 74.8420, "Car", "UNDER_REVIEW", 7),
    ("Exposed electrical cable near walkway", "A cable appears exposed beside the public walkway; residents are keeping clear and request a qualified inspection.", "Electrical Safety", "Urwa", 12.8890, 74.8390, "Walking / Pedestrian", "ASSIGNED", 1),
    ("Damaged bench in neighborhood garden", "A loose bench slat and unstable support need inspection before the seat is used again.", "Public Infrastructure", "Mannagudda", 12.8840, 74.8420, "Not Applicable", "RESOLVED", 21),
    ("Public toilet water tap and door need repair", "Visitors report a broken tap and a door that does not latch in the public toilet block.", "Public Infrastructure", "Hampankatta", 12.8670, 74.8410, "Walking / Pedestrian", "IN_PROGRESS", 9),
    ("Stray cattle obstructing service road", "A group of stray cattle is standing across part of the service road near the junction.", "Animal Control", "Kuloor", 12.9240, 74.8450, "Multiple Modes / General Traffic", "SUBMITTED", 2),
    ("Sewage overflowing into lane", "Wastewater is overflowing from a drain cover onto the lane; the source and safe cleanup need inspection.", "Drainage and Waterlogging", "Attavar", 12.8640, 74.8440, "Walking / Pedestrian", "UNDER_REVIEW", 1),
    ("Waterlogging at low point after rain", "Rainwater is collecting at the low point in the road and making the pedestrian crossing difficult to use.", "Drainage and Waterlogging", "Bolar", 12.8570, 74.8410, "Walking / Pedestrian", "ASSIGNED", 6),
    ("Construction debris narrowing footpath", "Loose construction debris is narrowing the footpath; pedestrians are stepping closer to moving traffic.", "Public Safety", "Kottara", 12.9060, 74.8520, "Walking / Pedestrian", "SUBMITTED", 4),
    ("Damaged road barrier beside curve", "A road barrier is leaning beside the curve and should be checked for safe placement.", "Transportation", "Derebail", 12.9010, 74.8660, "Car", "RESOLVED", 24),
    ("Curb ramp blocked by parked material", "Stored material blocks the curb ramp and makes the crossing difficult for wheelchair users.", "Roads and Infrastructure", "Valencia", 12.8580, 74.8510, "Walking / Pedestrian", "IN_PROGRESS", 11),
    ("Tree branches obstructing road edge", "Low branches extend into the road edge and reduce clearance for buses and other taller vehicles.", "Public Safety", "Surathkal", 13.0060, 74.7940, "Bus / Public Transport", "UNDER_REVIEW", 5),
]

STATUS_PATHS = {
    "SUBMITTED": ["SUBMITTED"],
    "UNDER_REVIEW": ["SUBMITTED", "UNDER_REVIEW"],
    "ASSIGNED": ["SUBMITTED", "UNDER_REVIEW", "ASSIGNED"],
    "IN_PROGRESS": ["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS"],
    "RESOLVED": ["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "RESOLVED"],
}
DEMO_PREFIX = "CIV-HACK-"


def seed_reports(db):
    initial_count = db.query(Report).count()
    inserted = skipped = already_present = 0
    now = datetime.now(timezone.utc)
    try:
        for index, item in enumerate(DEMO_REPORTS, start=1):
            title, description, category, location, latitude, longitude, transport, status, age_days = item
            public_id = f"{DEMO_PREFIX}{index:04d}"
            if db.query(Report).filter_by(public_id=public_id).first():
                skipped += 1
                already_present += 1
                continue

            created_at = now - timedelta(days=age_days, hours=index % 9)
            _, summary, score, level, explanation, factors, suggested = analyze(
                title, description, category, location, transport
            )
            report = Report(
                public_id=public_id, title=title, description=description, category=category,
                location_name=location, latitude=latitude, longitude=longitude,
                transportation_mode=transport, summary=summary, priority_score=score,
                priority_level=level, priority_explanation=explanation, priority_factors=factors,
                suggested_category=suggested, category_source="citizen", analysis_source="rules",
                status=status, created_at=created_at, updated_at=created_at,
            )
            if status in ("ASSIGNED", "IN_PROGRESS", "RESOLVED"):
                report.assigned_team = "Mangaluru Demo Public Works"
            if status == "RESOLVED":
                report.resolution_note = "Synthetic demonstration status only; no real-world repair is verified."
                report.resolved_at = created_at + timedelta(hours=12)

            db.add(report)
            db.flush()
            matches = candidates(report, db.query(Report).filter(Report.id != report.id).all())
            if matches:
                primary = db.query(Report).filter_by(public_id=matches[0]["public_id"]).first()
                report.primary_report_id = primary.id
                primary.duplicate_count += 1
                _, summary, score, level, explanation, factors, suggested = analyze(
                    title, description, category, location, transport, len(matches)
                )
                report.summary, report.priority_score, report.priority_level = summary, score, level
                report.priority_explanation, report.priority_factors = explanation, factors

            path = STATUS_PATHS[status]
            for step, new_status in enumerate(path):
                previous_status = path[step - 1] if step else None
                transition_at = created_at + timedelta(hours=step * 3)
                note = "Synthetic hackathon demonstration report; not a verified real-world incident."
                if new_status == "RESOLVED":
                    note = "Synthetic demo resolution status; physical work is not verified."
                report.history.append(StatusHistory(
                    previous_status=previous_status, new_status=new_status,
                    note=note, created_at=transition_at,
                ))
            if status in ("RESOLVED",):
                report.resolved_at = created_at + timedelta(hours=(len(path) - 1) * 3)
            inserted += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "initial_count": initial_count,
        "inserted": inserted,
        "skipped": skipped,
        "already_present": already_present,
        "final_count": db.query(Report).count(),
    }


def main():
    initialize_database()
    db = SessionLocal()
    try:
        result = seed_reports(db)
        print(
            "Synthetic demo seed (not verified incidents): "
            f"initial={result['initial_count']}, inserted={result['inserted']}, "
            f"skipped={result['skipped']}, already_present={result['already_present']}, "
            f"final={result['final_count']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
