import re
from collections import Counter
from .hotspot_service import find_hotspots
from .action_brief_service import generate
from .duplicate_service import CATEGORY_GROUPS

def answer(message: str, reports: list):
    text=message.casefold()
    ids=re.findall(r"CIV-[A-Z0-9-]+",message.upper())
    if ids:
        report=next((r for r in reports if r.public_id==ids[0]),None)
        if report:
            factors=report.priority_factors or {}
            detail="; ".join(f"{name} {item.get('score',0)}/{item.get('max',0)}" for name,item in factors.items())
            if "why" in text or "priorit" in text or "score" in text:
                return {"answer":f"{report.public_id} is {report.priority_level} at {report.priority_score}/100. {report.priority_explanation} Factor breakdown: {detail or 'Structured factor data is unavailable for this older record.'} Transportation mode: {report.transportation_mode or 'Not specified'}. This is a rules-based recommendation for human review.","complaint_ids":[report.public_id]}
            return {"answer":f"{report.public_id}: {report.title}. Status: {report.status.replace('_',' ').title()}. Category: {report.category}. Priority: {report.priority_level} ({report.priority_score}/100). Location: {report.location_name}. Transportation mode: {report.transportation_mode or 'Not specified'}.","complaint_ids":[report.public_id]}
        return {"answer":f"I couldn't find complaint {ids[0]}. Check the ID and try again.","complaint_ids":[]}
    active=[r for r in reports if r.status not in ("RESOLVED","REJECTED")]
    if "submit" in text or "report" in text and "how" in text:
        return {"answer":"Use Report an issue to enter a short title, description, category, locality, and optional coordinates and transportation mode. You can track the returned complaint ID. No account is required in this prototype."}
    if "track" in text:
        return {"answer":"Open Track, enter the CIV complaint ID, and select Find complaint. The status and timeline are read from the saved record."}
    if "after" in text and ("submit" in text or "complaint" in text):
        return {"answer":"After submission, the backend saves a complaint ID, runs rules-based category/summary/priority analysis, checks likely duplicates, and starts the report in Submitted. An administrator can review, assign, and update its status; the citizen can follow saved history by ID."}
    if "category" in text and ("choose" in text or "what" in text):
        return {"answer":"Choose the category that best describes the main problem. If uncertain, leave it unselected and the rules-based analyzer will suggest one from the description."}
    if ("pedestrian" in text or "walking" in text) and ("unresolved" in text or "open" in text):
        selected=[r for r in active if "pedestrian" in (r.transportation_mode or "").casefold() or "walking" in (r.transportation_mode or "").casefold()]
        return {"answer":f"{len(selected)} open complaint(s) are marked as affecting pedestrians or walking. This reflects the selected mode, not a measured count of affected people.","complaint_ids":[r.public_id for r in selected[:10]]}
    if "transport" in text or "pedestrian" in text or "mode" in text:
        counts=Counter((r.transportation_mode or "Not specified") for r in active)
        ordered=counts.most_common()
        return {"answer":"Open complaint transportation modes (from saved records): "+("; ".join(f"{name}: {count}" for name,count in ordered) if ordered else "no open reports yet")+". Mode is citizen-selected context, not a traffic-volume measurement."}
    if "hotspot" in text:
        hotspots=sorted(find_hotspots(reports),key=lambda h:h['count'],reverse=True)
        return {"answer":"Coordinate-based hotspots (same 1 km cluster rule): "+("; ".join(f"{h['name']}: {h['count']} reports, average priority {h['average_priority']}" for h in hotspots) if hotspots else "none identified from current located records")+"." ,"complaint_ids":[i for h in hotspots for i in h['report_ids']]}
    if "duplicate" in text or "related" in text:
        related=[r for r in reports if r.primary_report_id is not None]
        return {"answer":f"There are {len(related)} reports currently linked to a likely duplicate candidate. They remain separate submissions for administrator review.","complaint_ids":[r.public_id for r in related[:10]]}
    if "unassigned" in text or ("critical" in text and "complaint" in text):
        selected=[r for r in active if (r.priority_level=="CRITICAL" if "critical" in text else r.priority_level in ("HIGH","CRITICAL")) and (r.assigned_team is None or "unassigned" not in text)]
        if "unassigned" in text: selected=[r for r in selected if not r.assigned_team]
        return {"answer":f"{len(selected)} matching open high-priority complaint(s)"+(": "+", ".join(f"{r.public_id} ({r.title})" for r in selected[:8]) if selected else "."),"complaint_ids":[r.public_id for r in selected[:8]]}
    if "locality" in text or "area" in text or "location" in text:
        counts=Counter(r.location_name for r in active)
        return {"answer":"Open reports by locality: "+("; ".join(f"{name}: {count}" for name,count in counts.most_common(8)) if counts else "none")+"."}
    if "category" in text or "most" in text and "complaint" in text:
        counts=Counter(CATEGORY_GROUPS.get(r.category,r.category) for r in reports)
        return {"answer":f"The most reported category in the current dataset is {counts.most_common(1)[0][0]} ({counts.most_common(1)[0][1]} reports)." if counts else "There are no complaints in the current dataset."}
    if "open" in text or "unresolved" in text or "resolved" in text:
        if "resolved" in text:
            count=sum(r.status=="RESOLVED" for r in reports)
            return {"answer":f"{count} complaints are marked resolved in the database. That status records the demo workflow and is not independent verification of real-world repair."}
        return {"answer":f"{len(active)} complaints are currently open (not resolved or rejected) in the database."}
    if "assigned" in text:
        return {"answer":"Status meanings: Submitted is received; Under Review is being assessed; Assigned has a responsible team label; In Progress is marked as being addressed; Resolved means a resolution note was recorded. Database statuses are not independent proof of field work."}
    if "critical" in text and ("mean" in text or "what" in text):
        return {"answer":"Critical is the prototype's 75–100 score band. The five rules-based factors and their evidence are shown in Why this priority? A human should review each recommendation; it is not an official municipal standard."}
    if "brief" in text or "summar" in text:
        brief=generate(sorted(reports,key=lambda r:r.priority_score,reverse=True)[:20])
        return {"answer":(f"Current evidence-based brief: {brief['main_issue']} in {brief['location']}, {brief['supporting_report_count']} report(s), {brief['priority_summary']}. Suggested review: {brief['recommended_next_steps'][1]}" if brief else "There are no complaints to summarize."),"complaint_ids":brief["complaint_ids"] if brief else []}
    return {"answer":"I can help track a complaint ID, explain a saved priority score, summarize open or critical reports, compare transportation modes, identify hotspots, likely duplicates, categories, or localities. Try: “Why is CIV-… high priority?”"}
