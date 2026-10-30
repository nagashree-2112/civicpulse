import re
from .priority_service import priority

KEYWORDS = {
    "Roads": ["pothole", "road", "pavement", "crack", "asphalt", "footpath", "sidewalk"],
    "Water Supply": ["water supply", "water leak", "pipeline", "pipe burst", "water pipe", "no water", "low pressure"],
    "Waterlogging": ["waterlogging", "flood", "flooded", "waterlogged", "standing water"],
    "Drainage": ["drain", "sewer", "blocked", "overflow", "gutter"],
    "Waste Management": ["garbage", "waste", "trash", "rubbish", "dump", "collection"],
    "Streetlights": ["streetlight", "street light", "lamp", "dark", "lighting"],
    "Electrical Safety": ["electrical wire", "exposed wire", "live wire", "electric shock"],
    "Public Safety": ["danger", "unsafe", "hazard", "accident", "injury"],
    "Transportation": ["bus stop", "traffic", "transport", "road blockage"],
    "Public Infrastructure": ["bench", "park", "public building", "bridge", "public facility"],
    "Animal Control": ["stray dog", "animal", "livestock", "monkey"],
}

def analyze(title: str, description: str, supplied_category: str | None = None, location_name: str | None = None, transportation_mode: str | None = None, recurrence_count: int = 0):
    text = (title + " " + description).lower()
    counts = {category: sum(text.count(word) for word in words) for category, words in KEYWORDS.items()}
    suggested = max(counts, key=counts.get) if max(counts.values()) else "Other"
    category = supplied_category or suggested
    description_clean = re.sub(r"\s+", " ", description).strip()
    parts = [title.strip().rstrip(".") + ".", description_clean]
    if location_name and location_name.lower() not in description_clean.lower():
        parts.append(f"Location reported: {location_name.strip()}.")
    summary = re.sub(r"\s+", " ", " ".join(parts)).strip()
    if len(summary) > 320: summary = summary[:317].rsplit(" ", 1)[0] + "..."
    score, level, explanation, factors = priority(text, category, transportation_mode, recurrence_count)
    return category, summary, score, level, explanation, factors, suggested
