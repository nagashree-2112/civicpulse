from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from .database import initialize_database, engine, get_db
from .config import settings
from .models import Report, StatusHistory, WorkOrder, DuplicateReview, utcnow
from .schemas import ReportCreate, ReportOut, HistoryOut, AssignmentUpdate, StatusUpdate, WorkOrderCreate, WorkOrderUpdate, WorkOrderOut, DuplicateReviewCreate, CATEGORIES, STATUSES, TRANSPORT_MODES, ChatRequest
from .services.ai_service import analyze
from .services.duplicate_service import candidates
from .services.duplicate_service import CATEGORY_GROUPS
from .services.hotspot_service import find_hotspots
from .services.action_brief_service import generate
from .services.chat_service import answer as chat_answer
from .services.upload_service import UPLOAD_DIR, store_image

initialize_database()
app=FastAPI(title="CivicPulse AI",description="Rules-based civic complaint analysis and action tracking",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_methods=["*"],allow_headers=["*"])
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
app.mount("/uploads",StaticFiles(directory=str(UPLOAD_DIR)),name="uploads")

@app.get("/api/health")
def health(): return {"status":"ok"}

@app.post("/api/uploads")
async def upload_image(file:UploadFile=File(...)):
    return {"image_ref":await store_image(file)}

@app.post("/api/chat")
def civicpulse_chat(payload:ChatRequest,db:Session=Depends(get_db)):
    return chat_answer(payload.message,db.query(Report).all())

@app.post("/api/reports",response_model=ReportOut,status_code=201)
def create_report(payload:ReportCreate,db:Session=Depends(get_db)):
    if payload.image_ref and not (UPLOAD_DIR / payload.image_ref.rsplit("/",1)[-1]).is_file(): raise HTTPException(400,"Uploaded image was not found; upload it again")
    category,summary,score,level,explanation,factors,suggested=analyze(payload.title,payload.description,payload.category,payload.location_name,payload.transportation_mode)
    import uuid
    report=Report(public_id="CIV-"+uuid.uuid4().hex[:10].upper(),title=payload.title.strip(),description=payload.description.strip(),category=category,location_name=payload.location_name.strip(),latitude=payload.latitude,longitude=payload.longitude,image_ref=payload.image_ref,transportation_mode=payload.transportation_mode,summary=summary,priority_score=score,priority_level=level,priority_explanation=explanation,priority_factors=factors,suggested_category=suggested,category_source="citizen" if payload.category else "rules",analysis_source="rules",status="SUBMITTED")
    db.add(report); db.flush()
    matches=candidates(report,db.query(Report).filter(Report.id!=report.id).all())
    if matches:
        primary=db.query(Report).filter_by(public_id=matches[0]["public_id"]).first()
        report.primary_report_id=primary.id
        primary.duplicate_count+=1
        category,summary,score,level,explanation,factors,suggested=analyze(payload.title,payload.description,payload.category,payload.location_name,payload.transportation_mode,len(matches))
        report.summary,report.priority_score,report.priority_level=summary,score,level
        report.priority_explanation,report.priority_factors=explanation,factors
    report.history.append(StatusHistory(previous_status=None,new_status="SUBMITTED",note="Complaint submitted"))
    db.commit(); db.refresh(report); return report

@app.get("/api/reports")
def list_reports(q:str|None=None,category:str|None=None,status:str|None=None,priority:str|None=None,transportation_mode:str|None=None,locality:str|None=None,date_from:date|None=None,date_to:date|None=None,skip:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    query=apply_filters(db.query(Report),q,category,status,priority,transportation_mode,locality,date_from,date_to)
    total=query.count(); items=query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    return {"items":[ReportOut.model_validate(r) for r in items],"total":total,"skip":skip,"limit":limit}

def apply_filters(query,q=None,category=None,status=None,priority=None,transportation_mode=None,locality=None,date_from=None,date_to=None):
    if q: query=query.filter(or_(Report.title.ilike(f"%{q}%"),Report.description.ilike(f"%{q}%"),Report.public_id.ilike(f"%{q}%"),Report.location_name.ilike(f"%{q}%"),Report.transportation_mode.ilike(f"%{q}%")))
    if category:
        if category not in CATEGORIES: raise HTTPException(400,"Invalid category filter")
        group=CATEGORY_GROUPS.get(category,category)
        category_aliases=[name for name,target in CATEGORY_GROUPS.items() if target==group]
        query=query.filter(Report.category.in_(set(category_aliases+[category,group])))
    if status:
        if status not in STATUSES: raise HTTPException(400,"Invalid status filter")
        query=query.filter_by(status=status)
    if transportation_mode:
        if transportation_mode not in TRANSPORT_MODES and transportation_mode!="Not specified": raise HTTPException(400,"Invalid transportation mode filter")
        query=query.filter(Report.transportation_mode.is_(None)) if transportation_mode=="Not specified" else query.filter_by(transportation_mode=transportation_mode)
    if locality: query=query.filter(Report.location_name.ilike(f"%{locality}%"))
    if date_from and date_to and date_from>date_to: raise HTTPException(400,"Start date must not be after end date")
    if date_from: query=query.filter(Report.created_at>=datetime(date_from.year,date_from.month,date_from.day,tzinfo=timezone.utc))
    if date_to: query=query.filter(Report.created_at<datetime(date_to.year,date_to.month,date_to.day,tzinfo=timezone.utc)+timedelta(days=1))
    if priority:
        if priority.upper() not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"): raise HTTPException(400,"Invalid priority filter")
        query=query.filter_by(priority_level=priority.upper())
    return query

def get_report(public_id,db):
    r=db.query(Report).filter_by(public_id=public_id.upper()).first()
    if not r: raise HTTPException(404,"Complaint not found")
    return r
@app.get("/api/reports/{public_id}",response_model=ReportOut)
def report_detail(public_id:str,db:Session=Depends(get_db)): return get_report(public_id,db)
@app.get("/api/reports/{public_id}/history",response_model=list[HistoryOut])
def report_history(public_id:str,db:Session=Depends(get_db)): return get_report(public_id,db).history
@app.get("/api/reports/{public_id}/duplicates")
def report_duplicates(public_id:str,db:Session=Depends(get_db)):
    r=get_report(public_id,db); return candidates(r,db.query(Report).filter(Report.id!=r.id).all())

@app.get("/api/reports/{public_id}/duplicate-reviews")
def duplicate_reviews(public_id:str,db:Session=Depends(get_db)):
    r=get_report(public_id,db)
    rows=db.query(DuplicateReview).filter_by(report_id=r.id).all()
    return [{"candidate_id":db.query(Report.public_id).filter_by(id=x.candidate_report_id).scalar(),"decision":x.decision,"note":x.note,"updated_at":x.updated_at} for x in rows]

@app.post("/api/reports/{public_id}/duplicate-review")
def review_duplicate(public_id:str,payload:DuplicateReviewCreate,db:Session=Depends(get_db)):
    report=get_report(public_id,db); candidate=get_report(payload.candidate_id,db)
    if report.id==candidate.id: raise HTTPException(400,"A report cannot be reviewed as a duplicate of itself")
    possible=candidates(report,db.query(Report).filter(Report.id!=report.id).all())
    if candidate.public_id not in {x["public_id"] for x in possible}: raise HTTPException(404,"The selected report is not a current duplicate candidate")
    row=db.query(DuplicateReview).filter_by(report_id=report.id,candidate_report_id=candidate.id).first()
    if row is None: row=DuplicateReview(report_id=report.id,candidate_report_id=candidate.id,decision=payload.decision,note=payload.note.strip() if payload.note else None); db.add(row)
    else: row.decision=payload.decision; row.note=payload.note.strip() if payload.note else None; row.updated_at=utcnow()
    db.commit(); db.refresh(row)
    return {"candidate_id":candidate.public_id,"decision":row.decision,"note":row.note,"updated_at":row.updated_at}
@app.get("/api/analytics/summary")
def analytics(q:str|None=None,category:str|None=None,status:str|None=None,priority:str|None=None,transportation_mode:str|None=None,locality:str|None=None,date_from:date|None=None,date_to:date|None=None,db:Session=Depends(get_db)):
    reports=apply_filters(db.query(Report),q,category,status,priority,transportation_mode,locality,date_from,date_to).all()
    count=lambda fn:sum(bool(fn(r)) for r in reports)
    by=lambda key:{value:sum(getattr(r,key)==value for r in reports) for value in sorted(set(getattr(r,key) for r in reports))}
    transport=lambda r:r.transportation_mode or "Not specified"
    transport_counts={mode:sum(transport(r)==mode for r in reports) for mode in sorted({transport(r) for r in reports})}
    priority_by_transport={mode:{level:sum(transport(r)==mode and r.priority_level==level for r in reports) for level in ("LOW","MEDIUM","HIGH","CRITICAL")} for mode in transport_counts}
    dates={r.created_at.date().isoformat():sum(x.created_at.date()==r.created_at.date() for x in reports) for r in reports}
    locality={r.location_name:sum(x.location_name==r.location_name for x in reports) for r in reports}
    resolved=[r for r in reports if r.resolved_at]
    open_count=count(lambda r:r.status not in ("RESOLVED","REJECTED"))
    category_counts=Counter(CATEGORY_GROUPS.get(r.category,r.category) for r in reports)
    most_common=category_counts.most_common(1)
    insights=[]
    if most_common: insights.append(f"In this demo dataset, {most_common[0][0]} is the largest category with {most_common[0][1]} report(s).")
    urgent=[r for r in reports if r.status not in ("RESOLVED","REJECTED") and r.priority_level in ("HIGH","CRITICAL")]
    if urgent: insights.append(f"{len(urgent)} high or critical complaint(s) remain open in the selected records.")
    return {"total":len(reports),"new":count(lambda r:r.status in ("SUBMITTED","UNDER_REVIEW")),"high_critical":count(lambda r:r.priority_level in ("HIGH","CRITICAL")),"in_progress":count(lambda r:r.status=="IN_PROGRESS"),"resolved":count(lambda r:r.status=="RESOLVED"),"open":open_count,"resolution_rate":round(100*len(resolved)/len(reports),1) if reports else 0,"by_category":dict(category_counts),"by_priority":by("priority_level"),"by_status":by("status"),"by_transportation_mode":transport_counts,"priority_by_transportation_mode":priority_by_transport,"by_date":dict(sorted(dates.items())),"by_locality":locality,"duplicates":sum(r.primary_report_id is not None for r in reports),"hotspots":find_hotspots(reports),"insights":insights}
@app.get("/api/analytics/hotspots")
def hotspots(db:Session=Depends(get_db)): return find_hotspots(db.query(Report).all())
@app.post("/api/admin/action-brief")
def action_brief(category:str|None=None,location:str|None=None,db:Session=Depends(get_db)):
    query=apply_filters(db.query(Report),category=category,locality=location)
    brief=generate(query.order_by(Report.priority_score.desc()).limit(20).all())
    if not brief: raise HTTPException(404,"No reports match the selected filters")
    return brief
@app.patch("/api/admin/reports/{public_id}/assignment",response_model=ReportOut)
def assign(public_id:str,payload:AssignmentUpdate,db:Session=Depends(get_db)):
    r=get_report(public_id,db); r.assigned_team=payload.team.strip(); db.commit(); db.refresh(r); return r

TRANSITIONS={"SUBMITTED":{"UNDER_REVIEW","REJECTED"},"UNDER_REVIEW":{"ASSIGNED","REJECTED"},"ASSIGNED":{"IN_PROGRESS","REJECTED"},"IN_PROGRESS":{"RESOLVED"},"RESOLVED":set(),"REJECTED":set()}
@app.patch("/api/admin/reports/{public_id}/status",response_model=ReportOut)
def update_status(public_id:str,payload:StatusUpdate,db:Session=Depends(get_db)):
    r=get_report(public_id,db); target=payload.status.upper()
    if target not in STATUSES: raise HTTPException(400,"Invalid status")
    if target not in TRANSITIONS[r.status]: raise HTTPException(400,f"Invalid transition from {r.status} to {target}")
    if target=="ASSIGNED" and not r.assigned_team: raise HTTPException(400,"Assign a responsible team before moving to ASSIGNED")
    if target=="RESOLVED" and not (payload.note and payload.note.strip()): raise HTTPException(400,"A resolution note is required")
    if target=="REJECTED" and not (payload.note and payload.note.strip()): raise HTTPException(400,"An explanation is required to reject a complaint")
    previous=r.status; r.status=target; r.updated_at=utcnow()
    if target=="RESOLVED": r.resolution_note=payload.note.strip(); r.resolved_at=utcnow()
    r.history.append(StatusHistory(previous_status=previous,new_status=target,note=payload.note))
    db.commit(); db.refresh(r); return r

@app.get("/api/admin/work-orders",response_model=list[WorkOrderOut])
def list_work_orders(status:str|None=None,db:Session=Depends(get_db)):
    query=db.query(WorkOrder)
    if status:
        if status not in ("PLANNED","IN_PROGRESS","COMPLETED","CANCELLED"): raise HTTPException(400,"Invalid work order status")
        query=query.filter_by(status=status)
    return query.order_by(WorkOrder.created_at.desc()).all()

@app.post("/api/admin/work-orders",response_model=WorkOrderOut,status_code=201)
def create_work_order(payload:WorkOrderCreate,db:Session=Depends(get_db)):
    report=get_report(payload.report_id,db)
    order=WorkOrder(report_id=report.id,title=payload.title.strip(),assigned_team=payload.assigned_team.strip() if payload.assigned_team else None,estimated_workers=payload.estimated_workers,estimated_hours=payload.estimated_hours,materials=[x.strip()[:100] for x in payload.materials if x.strip()],assumptions=payload.assumptions.strip(),notes=payload.notes.strip() if payload.notes else None)
    db.add(order); db.commit(); db.refresh(order); return order

@app.patch("/api/admin/work-orders/{order_id}",response_model=WorkOrderOut)
def update_work_order(order_id:int,payload:WorkOrderUpdate,db:Session=Depends(get_db)):
    order=db.query(WorkOrder).filter_by(id=order_id).first()
    if not order: raise HTTPException(404,"Work order not found")
    if payload.status and payload.status not in ("PLANNED","IN_PROGRESS","COMPLETED","CANCELLED"): raise HTTPException(400,"Invalid work order status")
    allowed={"PLANNED":{"IN_PROGRESS","CANCELLED"},"IN_PROGRESS":{"COMPLETED","CANCELLED"},"COMPLETED":set(),"CANCELLED":set()}
    if payload.status and payload.status!=order.status and payload.status not in allowed[order.status]: raise HTTPException(400,f"Invalid work order transition from {order.status} to {payload.status}")
    changes=payload.model_dump(exclude_unset=True)
    if "assigned_team" in changes and changes["assigned_team"] is not None: changes["assigned_team"]=changes["assigned_team"].strip()
    if "materials" in changes and changes["materials"] is not None: changes["materials"]=[x.strip()[:100] for x in changes["materials"] if x.strip()]
    if "notes" in changes and changes["notes"] is not None: changes["notes"]=changes["notes"].strip()
    for key,value in changes.items(): setattr(order,key,value)
    order.updated_at=utcnow(); db.commit(); db.refresh(order); return order

@app.get("/api/reports/{public_id}/resource-plan")
def resource_plan(public_id:str,db:Session=Depends(get_db)):
    report=get_report(public_id,db)
    category=report.category.lower()
    if any(word in category for word in ("road","infrastructure")):
        workers,hours,materials=2,4,["Road inspection kit","Repair materials to be determined after inspection"]
        department="Roads maintenance"
    elif any(word in category for word in ("drain","waterlog")):
        workers,hours,materials=2,3,["Drain inspection tools","Protective equipment"]
        department="Drainage and water"
    elif any(word in category for word in ("electrical","lighting")):
        workers,hours,materials=2,2,["Electrical test equipment","Qualified personnel required"]
        department="Electrical maintenance"
    elif any(word in category for word in ("waste","sanitation","garbage")):
        workers,hours,materials=2,2,["Collection equipment to be confirmed"]
        department="Sanitation services"
    else:
        workers,hours,materials=2,3,["Determine equipment after site inspection"]
        department="Relevant service team (confirm locally)"
    return {"report_id":report.public_id,"recommended_department":department,"estimated_workers":workers,"estimated_hours":hours,"materials":materials,"confidence":"LOW — heuristic planning estimate","assumptions":"Initial inspection only. Actual crew size, duration, equipment, materials, access, and safety controls must be confirmed on site. This estimate is not a dispatch or work completion record.","active_team_work_orders":db.query(WorkOrder).filter(WorkOrder.status.in_(["PLANNED","IN_PROGRESS"]),WorkOrder.assigned_team.is_not(None)).count()}
