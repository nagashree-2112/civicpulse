from .duplicate_service import CATEGORY_GROUPS

def generate(reports):
    if not reports: return None
    groups={}
    for r in reports: groups.setdefault((CATEGORY_GROUPS.get(r.category,r.category),r.location_name),[]).append(r)
    (main,location),reports=max(groups.items(),key=lambda item:(len(item[1]),sum(r.priority_score for r in item[1])/len(item[1])))
    priority_distribution={level:sum(r.priority_level==level for r in reports) for level in ("LOW","MEDIUM","HIGH","CRITICAL")}
    modes={}
    for r in reports:
        mode=r.transportation_mode or "Not specified"
        modes[mode]=modes.get(mode,0)+1
    safety=[r.public_id for r in reports if (r.priority_factors or {}).get("Safety Risk",{}).get("score",0)>=18]
    recommendation={"Water Supply":"Inspect the reported supply or pipeline issue and refer it to the water maintenance team.","Roads and Infrastructure":"Inspect the reported road or footpath and schedule appropriate repairs.","Drainage and Waterlogging":"Inspect drainage and restore safe water flow.","Sanitation and Garbage":"Review collection coverage and arrange a sanitation inspection.","Electrical Safety":"Keep people clear of the hazard and request an electrical safety inspection.","Street Lighting":"Inspect the lighting asset and schedule maintenance."}.get(main,"Verify the reported conditions and refer them to the responsible service team.")
    return {"main_issue":main,"location":location,"supporting_report_count":len(reports),"complaint_ids":[r.public_id for r in reports],"priority_summary":f"{sum(r.priority_score for r in reports)//len(reports)} average priority; {sum(r.priority_level in ('HIGH','CRITICAL') for r in reports)} high or critical","priority_distribution":priority_distribution,"transportation_modes":modes,"safety_concern_ids":safety,"recommended_next_steps":["Verify the reported conditions on site.",recommendation,"Update affected residents when work is scheduled and completed."],"evidence_summary":" ".join(r.summary for r in reports[:3])}
