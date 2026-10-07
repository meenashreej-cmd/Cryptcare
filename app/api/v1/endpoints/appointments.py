"""
Appointment endpoints for CryptCare API.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.appointment import AppointmentStatusEnum
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentUpdateRequest,
    AppointmentResponse,
    AppointmentListResponse,
    AppointmentStatsResponse
)
from app.services import appointment_service

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("", response_model=AppointmentResponse, status_code=201)
@router.post("/", response_model=AppointmentResponse, status_code=201)
def create_appointment(
    request: AppointmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Create a new appointment"""
    appointment = appointment_service.create_appointment(db, request, current_user.id)
    return appointment_service.to_appointment_response(appointment)


@router.get("", response_model=AppointmentListResponse)
@router.get("/", response_model=AppointmentListResponse)
def list_appointments(
    status_filter: Optional[AppointmentStatusEnum] = Query(None, description="Filter by appointment status"),
    from_date: Optional[datetime] = Query(None, description="Filter appointments from this date"),
    to_date: Optional[datetime] = Query(None, description="Filter appointments until this date"),
    limit: int = Query(50, ge=1, le=100, description="Number of appointments to return"),
    offset: int = Query(0, ge=0, description="Number of appointments to skip"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List appointments for the current user"""
    appointments = appointment_service.get_appointments_for_user(
        db, 
        current_user.id, 
        current_user.role,
        status_filter=status_filter,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )
    
    appointment_responses = [
        appointment_service.to_appointment_response(apt) 
        for apt in appointments
    ]
    
    return AppointmentListResponse(
        appointments=appointment_responses,
        total=len(appointment_responses)
    )


@router.get("/upcoming", response_model=AppointmentListResponse)
def get_upcoming_appointments(
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get upcoming appointments for the next N days"""
    appointments = appointment_service.get_upcoming_appointments(
        db, current_user.id, current_user.role, days_ahead
    )
    
    appointment_responses = [
        appointment_service.to_appointment_response(apt) 
        for apt in appointments
    ]
    
    return AppointmentListResponse(
        appointments=appointment_responses,
        total=len(appointment_responses)
    )


@router.get("/stats", response_model=AppointmentStatsResponse)
def get_appointment_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get appointment statistics for the current user"""
    return appointment_service.get_appointment_stats(db, current_user.id, current_user.role)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific appointment by ID"""
    appointment = appointment_service.get_appointment_by_id(
        db, appointment_id, current_user.id, current_user.role
    )
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return appointment_service.to_appointment_response(appointment)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    request: AppointmentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Update an existing appointment"""
    appointment = appointment_service.update_appointment(
        db, appointment_id, request, current_user.id, current_user.role
    )
    return appointment_service.to_appointment_response(appointment)


@router.delete("/{appointment_id}", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Cancel an appointment"""
    appointment = appointment_service.cancel_appointment(
        db, appointment_id, current_user.id, current_user.role
    )
    return appointment_service.to_appointment_response(appointment)