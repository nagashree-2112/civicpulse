"""Deterministic greedy map clusters: same anchor within 1 km, minimum two reports."""
from collections import Counter
from .duplicate_service import _distance
from .duplicate_service import CATEGORY_GROUPS

DISTANCE_METERS = 1000
MIN_REPORTS = 2

def find_hotspots(reports):
    located=sorted((r for r in reports if r.latitude is not None and r.longitude is not None),key=lambda r:r.public_id)
    seen=set(); groups=[]
    for anchor in located:
        if anchor.id in seen: continue
        group=[r for r in located if r.id not in seen and _distance(anchor,r) is not None and _distance(anchor,r)<=DISTANCE_METERS]
        if len(group)<MIN_REPORTS: continue
        seen.update(r.id for r in group)
        categories=Counter(CATEGORY_GROUPS.get(r.category,r.category) for r in group)
        modes=Counter(r.transportation_mode or "Not specified" for r in group)
        locations=Counter(r.location_name for r in group)
        dominant=categories.most_common(1)[0][0]
        high=sum(r.priority_score>=50 for r in group)
        ids=[r.public_id for r in group]
        groups.append({"name":locations.most_common(1)[0][0],"category":dominant,"location_name":locations.most_common(1)[0][0],"latitude":sum(r.latitude for r in group)/len(group),"longitude":sum(r.longitude for r in group)/len(group),"count":len(group),"report_ids":ids,"category_counts":dict(categories),"transportation_modes":dict(modes),"average_priority":round(sum(r.priority_score for r in group)/len(group),1),"priority_summary":f"{round(sum(r.priority_score for r in group)/len(group))} average priority","dominant_issue":dominant,"suggested_action":f"Review the {dominant.lower()} reports in {locations.most_common(1)[0][0]} and assign the responsible team.","high_priority_count":high})
    return groups
