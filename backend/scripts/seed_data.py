"""Insert 45 deterministic, fictional reports. Safe to run repeatedly; never clears the DB."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import initialize_database, SessionLocal
from app.models import Report, StatusHistory
from app.services.ai_service import analyze
from app.services.duplicate_service import candidates

initialize_database()
CASES=[
 ("Deep pothole near school entrance","A deep pothole near the school entrance forces two-wheelers to swerve. Students and pedestrians use this road.","Roads","Two-Wheeler / Motorcycle","School Road"),
 ("Pothole by school gate","A large pothole beside the school gate is forcing motorcycles into traffic.","Roads","Bicycle","School Road"),
 ("Broken pedestrian footpath","Loose paving stones make the footpath difficult to use for people walking.","Roads","Walking / Pedestrian","School Road"),
 ("Water supply interruption","Residents report no water supply since yesterday morning.","Water Supply","Not Applicable","Maple Ward"),
 ("Pipeline leak at Maple crossing","Water is leaking from a pipe near the Maple crossing and running along the road.","Water Supply","Multiple Modes / General Traffic","Maple Ward"),
 ("Overflowing community garbage bin","Garbage is overflowing from the public bin beside the community market.","Waste Management","Not Applicable","Market Square"),
 ("Missed waste collection","The scheduled waste collection was missed for several days near the market.","Waste Management","Not Applicable","Market Square"),
 ("Blocked drain after rain","A blocked drain is causing standing water outside nearby homes.","Drainage","Walking / Pedestrian","River Lane"),
 ("Waterlogging at bus stop","Waterlogging makes it difficult to reach the bus stop safely.","Waterlogging","Bus / Public Transport","River Lane"),
 ("Street light not working","The streetlight has been out for three nights along the park footpath.","Streetlights","Walking / Pedestrian","Lake Park"),
 ("Exposed electrical wire","An exposed electrical wire hangs beside the public footpath near the clinic.","Electrical Safety","Walking / Pedestrian","Clinic Road"),
 ("Damaged public bench","A damaged bench in the public garden needs inspection and repair.","Public Infrastructure","Not Applicable","Lake Park"),
 ("Bus stop access obstruction","A road barrier blocks wheelchair and pedestrian access to the bus stop.","Transportation","Bus / Public Transport","Civic Avenue"),
 ("Stray dogs near playground","Several stray dogs are gathering beside the children's playground.","Animal Control","Walking / Pedestrian","Lake Park"),
 ("Road obstruction near market","A fallen branch is blocking part of the busy road near the market.","Public Safety","Multiple Modes / General Traffic","Market Square"),
]
STATUSES=["SUBMITTED","UNDER_REVIEW","ASSIGNED","IN_PROGRESS","RESOLVED","SUBMITTED","UNDER_REVIEW","ASSIGNED","IN_PROGRESS","SUBMITTED"]
TRANSITIONS={"SUBMITTED":["UNDER_REVIEW","ASSIGNED","IN_PROGRESS","RESOLVED"],"UNDER_REVIEW":["ASSIGNED","IN_PROGRESS","RESOLVED"],"ASSIGNED":["IN_PROGRESS","RESOLVED"],"IN_PROGRESS":["RESOLVED"]}
db=SessionLocal()
try:
    initialize_database()
    created=0
    for i in range(45):
        base_title,description,category,mode,location=CASES[i%len(CASES)]
        cycle=i//len(CASES)
        title=base_title if cycle==0 else f"{base_title} report {cycle+1}"
        public_id=f"CIV-DEMO-{i+1:04d}"
        if db.query(Report).filter_by(public_id=public_id).first(): continue
        lat=12.9716+((i%5)-2)*0.0012
        lon=77.5946+(((i//5)%4)-1.5)*0.0012
        if i%7==0: lat=lon=None
        transport=None if i%11==0 else mode
        cat,summary,score,level,explanation,factors,suggested=analyze(title,description,category,location,transport)
        report=Report(public_id=public_id,title=title,description=description,category=cat,location_name=location,latitude=lat,longitude=lon,transportation_mode=transport,summary=summary,priority_score=score,priority_level=level,priority_explanation=explanation,priority_factors=factors,suggested_category=suggested,category_source="citizen",analysis_source="rules",status=STATUSES[i%len(STATUSES)],created_at=datetime.now(timezone.utc)-timedelta(days=(i*3)%45))
        db.add(report); db.flush()
        related=candidates(report,db.query(Report).filter(Report.id!=report.id).all())
        if related:
            primary=db.query(Report).filter_by(public_id=related[0]["public_id"]).first()
            report.primary_report_id=primary.id; primary.duplicate_count+=1
            cat,summary,score,level,explanation,factors,suggested=analyze(title,description,category,location,transport,len(related))
            report.summary,report.priority_score,report.priority_level=summary,score,level
            report.priority_explanation,report.priority_factors=explanation,factors
        report.history.append(StatusHistory(previous_status=None,new_status="SUBMITTED",note="Fictional demonstration complaint"))
        previous="SUBMITTED"
        for new_status in TRANSITIONS[previous][:TRANSITIONS[previous].index(report.status)+1] if report.status in TRANSITIONS[previous] else []:
            report.history.append(StatusHistory(previous_status=previous,new_status=new_status,note=f"Synthetic demo transition to {new_status}")); previous=new_status
            if new_status==report.status: break
        if report.status=="RESOLVED": report.resolution_note="Fictional demo resolution note"; report.resolved_at=report.created_at+timedelta(days=1)
        if report.status in ("ASSIGNED","IN_PROGRESS","RESOLVED"): report.assigned_team="Civic maintenance demo team"
        created+=1
    db.commit()
    print(f"Inserted {created} fictional demo reports; database total: {db.query(Report).count()}")
finally: db.close()
