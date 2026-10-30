"""Transparent prototype scoring. Not an official municipal standard."""
from __future__ import annotations

LIMITS = {"Safety Risk": 30, "Severity": 25, "Public Impact": 20, "Recurrence": 15, "Time Sensitivity": 10}

def label_for_score(score: int) -> str:
    return "CRITICAL" if score >= 75 else "HIGH" if score >= 50 else "MEDIUM" if score >= 25 else "LOW"

def priority(text: str, category: str, transportation_mode: str | None = None, recurrence_count: int = 0):
    value = text.lower()
    transport = transportation_mode or "Not specified"
    safety = 4
    safety_reason = "No explicit immediate safety hazard was described; a conservative baseline is used."
    if any(term in value for term in ("exposed wire", "live wire", "electrical wire", "electrocution")):
        safety, safety_reason = 28, "An exposed or live electrical wire can cause serious injury."
    elif any(term in value for term in ("injury", "accident", "danger", "unsafe", "hazard", "collapse", "fire")):
        safety, safety_reason = 22, "The description explicitly identifies a danger, hazard, accident, or injury risk."
    elif any(term in value for term in ("pothole", "broken footpath", "damaged footpath", "open manhole", "blocked road")):
        safety, safety_reason = 15, "The reported road or pedestrian obstruction may create a safety risk."
    mode_context = ""
    mode_lower = transport.lower()
    if any(term in value for term in ("pothole", "footpath", "sidewalk", "road obstruction")):
        if "two-wheeler" in mode_lower or "bicycle" in mode_lower:
            safety = min(30, safety + 5)
            mode_context = f" The selected {transport} mode is relevant to road stability; this is an inferred concern, not measured traffic data."
        elif "pedestrian" in mode_lower or "walking" in mode_lower:
            safety = min(30, safety + 4)
            mode_context = " The selected pedestrian mode is relevant to access and exposure; this is an inference, not a measured injury risk."
    if any(term in value for term in ("exposed wire", "live wire", "collapse", "major leak", "burst pipe", "fire")):
        severity, severity_reason = 23, "The described failure could cause substantial service disruption or harm."
    elif any(term in value for term in ("overflow", "waterlogging", "blocked drain", "deep pothole", "large pothole", "broken pipe")):
        severity, severity_reason = 18, "The description indicates a substantial infrastructure or service problem."
    elif any(term in value for term in ("broken", "damaged", "not working", "missed collection", "leaking")):
        severity, severity_reason = 13, "A service or asset is reported damaged or unavailable."
    else:
        severity, severity_reason = 7, "The description does not provide evidence of severe damage; a conservative score is used."
    if any(term in value for term in ("school", "hospital", "main road", "bus stop", "many residents", "community", "market")):
        impact, impact_reason = 16, "A public place or shared service is mentioned, suggesting broader potential impact."
    elif any(term in value for term in ("street", "neighborhood", "locality", "footpath", "sidewalk")):
        impact, impact_reason = 11, "A shared neighborhood area is mentioned; the number affected is unknown."
    else:
        impact, impact_reason = 6, "The affected area or number of people is not specified."
    recurrence = min(15, 5 * max(0, recurrence_count))
    recurrence_reason = (f"{recurrence_count} related existing report(s) support a recurrence signal." if recurrence_count else "No corroborating history was found; recurrence is scored conservatively.")
    if any(term in value for term in ("urgent", "immediate", "emergency", "right away", "currently blocking")):
        time_score, time_reason = 10, "Urgent or active impact is explicitly described."
    elif any(term in value for term in ("ongoing", "several days", "since yesterday", "for days")):
        time_score, time_reason = 7, "The description indicates an ongoing issue."
    else:
        time_score, time_reason = 4, "No specific time pressure is stated."
    scores = {"Safety Risk": safety, "Severity": severity, "Public Impact": impact, "Recurrence": recurrence, "Time Sensitivity": time_score}
    reasons = {"Safety Risk": safety_reason + mode_context, "Severity": severity_reason, "Public Impact": impact_reason, "Recurrence": recurrence_reason, "Time Sensitivity": time_reason}
    factors = {name: {"score": scores[name], "max": maximum, "reason": reasons[name]} for name, maximum in LIMITS.items()}
    score = min(100, sum(item["score"] for item in factors.values()))
    level = label_for_score(score)
    top = sorted(factors.items(), key=lambda item: item[1]["score"] / item[1]["max"], reverse=True)[:2]
    main_reasons = " and ".join(name.lower() for name, _ in top)
    uncertainty = " Evidence is limited to the submitted description and available related reports."
    explanation = f"{level.title()} ({score}/100): {main_reasons} contribute most to this recommendation. " + " ".join(reasons.values()) + uncertainty + " This prototype score requires human review."
    return score, level, explanation, factors
