from datetime import datetime
import re
from pydantic import BaseModel, ConfigDict, Field, model_validator

CATEGORIES = ["Roads", "Waterlogging", "Drainage", "Waste Management", "Streetlights", "Public Safety", "Other", "Roads and Infrastructure", "Water Supply", "Sanitation and Garbage", "Drainage and Waterlogging", "Street Lighting", "Electrical Safety", "Public Infrastructure", "Transportation", "Animal Control"]
STATUSES = ["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED"]
TRANSPORT_MODES = ["Walking / Pedestrian", "Bicycle", "Two-Wheeler / Motorcycle", "Car", "Auto-Rickshaw", "Bus / Public Transport", "Truck / Heavy Vehicle", "Multiple Modes / General Traffic", "Not Applicable", "Other"]

class ReportCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    category: str | None = None
    location_name: str = Field(min_length=2, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    image_ref: str | None = Field(default=None, max_length=500)
    transportation_mode: str | None = Field(default=None, max_length=60)
    @model_validator(mode="after")
    def valid_location(self):
        if (self.latitude is None) != (self.longitude is None): raise ValueError("Latitude and longitude must be provided together")
        if self.category and self.category not in CATEGORIES: raise ValueError("Invalid category")
        if self.transportation_mode and self.transportation_mode not in TRANSPORT_MODES: raise ValueError("Invalid transportation mode")
        if self.image_ref and not re.fullmatch(r"/uploads/[a-f0-9]{32}\.(png|jpg|gif|webp)", self.image_ref): raise ValueError("Image reference must come from the upload service")
        return self

class AssignmentUpdate(BaseModel): team: str = Field(min_length=2, max_length=100)
class StatusUpdate(BaseModel): status: str; note: str | None = Field(default=None, max_length=1000)
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; public_id: str; title: str; description: str; category: str; location_name: str
    latitude: float | None; longitude: float | None; summary: str; priority_score: int; priority_level: str
    priority_explanation: str; priority_factors: dict | None = None; transportation_mode: str | None = None
    suggested_category: str | None = None; category_source: str | None = None; analysis_source: str | None = None; image_ref: str | None = None
    primary_report_id: int | None; duplicate_count: int; assigned_team: str | None
    status: str; resolution_note: str | None; created_at: datetime; updated_at: datetime; resolved_at: datetime | None
class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    previous_status: str | None; new_status: str; note: str | None; created_at: datetime

class ChatRequest(BaseModel): message: str = Field(min_length=1, max_length=1000)
class ChatResponse(BaseModel): answer: str; complaint_ids: list[str] = Field(default_factory=list)

class WorkOrderCreate(BaseModel):
    report_id: str = Field(min_length=8, max_length=24)
    title: str = Field(min_length=4, max_length=180)
    assigned_team: str | None = Field(default=None, min_length=2, max_length=100)
    estimated_workers: int | None = Field(default=None, ge=1, le=500)
    estimated_hours: float | None = Field(default=None, gt=0, le=10000)
    materials: list[str] = Field(default_factory=list, max_length=30)
    assumptions: str = Field(min_length=10, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

class WorkOrderUpdate(BaseModel):
    status: str | None = None
    assigned_team: str | None = Field(default=None, min_length=2, max_length=100)
    estimated_workers: int | None = Field(default=None, ge=1, le=500)
    estimated_hours: float | None = Field(default=None, gt=0, le=10000)
    materials: list[str] | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=2000)

class WorkOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; report_id: int; title: str; status: str; assigned_team: str | None
    estimated_workers: int | None; estimated_hours: float | None; materials: list | None
    assumptions: str; notes: str | None; created_at: datetime; updated_at: datetime

class DuplicateReviewCreate(BaseModel):
    candidate_id: str = Field(min_length=8, max_length=24)
    decision: str
    note: str | None = Field(default=None, max_length=1000)
    @model_validator(mode="after")
    def valid_decision(self):
        if self.decision not in ("CONFIRMED", "DISMISSED"):
            raise ValueError("Decision must be CONFIRMED or DISMISSED")
        return self
