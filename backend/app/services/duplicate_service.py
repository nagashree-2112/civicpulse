import re
from math import radians, sin, cos, sqrt, atan2
from .ai_service import KEYWORDS

CATEGORY_GROUPS={"Roads":"Roads and Infrastructure","Waterlogging":"Drainage and Waterlogging","Drainage":"Drainage and Waterlogging","Waste Management":"Sanitation and Garbage","Streetlights":"Street Lighting"}

def _tokens(text): return set(re.findall(r"[a-z]{3,}", text.lower()))
def _distance(a, b):
    if None in (a.latitude, a.longitude, b.latitude, b.longitude): return None
    p1,p2=radians(a.latitude),radians(b.latitude); dp=p2-p1; dl=radians(b.longitude-a.longitude)
    x=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
    return 6371000*2*atan2(sqrt(x),sqrt(1-x))
def candidates(report, reports):
    results=[]; terms=_tokens(report.title+" "+report.description)
    for other in reports:
        same_category=CATEGORY_GROUPS.get(other.category,other.category)==CATEGORY_GROUPS.get(report.category,report.category)
        if other.id == report.id or not same_category: continue
        other_terms=_tokens(other.title+" "+other.description)
        common=len(terms&other_terms)/max(1,len(terms|other_terms))
        distance=_distance(report,other)
        if common >= .25 and (distance is None or distance <= 500):
            location_match=report.location_name.strip().casefold()==other.location_name.strip().casefold()
            mode_match=bool(report.transportation_mode and report.transportation_mode==other.transportation_mode)
            score=min(1.0,common+(0.1 if location_match else 0)+(0.05 if mode_match else 0))
            explanation="Similar title/description and category"
            if location_match: explanation+="; same reported locality"
            if distance is not None: explanation+=f"; coordinates are {round(distance)} m apart"
            if mode_match: explanation+="; same transportation mode"
            results.append({"public_id":other.public_id,"title":other.title,"location_name":other.location_name,"similarity":round(score,2),"distance_m":round(distance) if distance is not None else None,"explanation":explanation})
    return sorted(results,key=lambda x:x["similarity"],reverse=True)[:5]
