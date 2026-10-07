"""
Appointment service for CryptCare.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.appointment import Appointment, AppointmentStatusEnum, AppointmentTypeEnum
from app.models.user import User, RoleEnum
from app.schemas.appointment import (
    AppointmentCreateRequest, 
    AppointmentUpdateRequest, 
    AppointmentResponse,
    AppointmentStatsResponse
)


def create_appointment(
    db: Session, 
    request: AppointmentCreateRequest, 
    created_by_user_id: str
) -> Appointment:
    """Create a new appointment"""
    
    # Validate patient exists and is a patient
    patient = db.query(User).filter(
        User.user_id == request.patient_id,
        User.role == RoleEnum.PATIENT
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Validate doctor exists and is a doctor
    doctor = db.query(User).filter(
        User.user_id == request.doctor_id,
        User.role == RoleEnum.DOCTOR
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Check for scheduling conflicts (optional)
    existing_appointment = db.query(Appointment).filter(
        Appointment.doctor_id == request.doctor_id,
        Appointment.scheduled_datetime == request.scheduled_datetime,
        Appointment.status.in_([
            AppointmentStatusEnum.SCHEDULED,
            AppointmentStatusEnum.CONFIRMED,
            AppointmentStatusEnum.IN_PROGRESS
        ])
    ).first()
    
    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor already has an appointment scheduled at this time"
        )
    
    appointment = Appointment(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        scheduled_datetime=request.scheduled_datetime,
        duration_minutes=request.duration_minutes,
        appointment_type=request.appointment_type,
        title=request.title,
        description=request.description,
        location=request.location,
        is_virtual=request.is_virtual,
        virtual_meeting_link=request.virtual_meeting_link,
        created_by=created_by_user_id
    )
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    return appointment


def get_appointment_by_id(db: Session, appointment_id: str, user_id: str, user_role: str) -> Optional[Appointment]:
    """Get appointment by ID with access control"""
    query = db.query(Appointment).filter(Appointment.appointment_id == appointment_id)
    
    # Apply access control based on user role
    if user_role == RoleEnum.PATIENT.value:
        query = query.filter(Appointment.patient_id == user_id)
    elif user_role == RoleEnum.DOCTOR.value:
        query = query.filter(Appointment.doctor_id == user_id)
    elif user_role not in [RoleEnum.ADMIN.value, RoleEnum.HOSPITAL_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access appointments"
        )
    
    return query.first()


def get_appointments_for_user(
    db: Session, 
    user_id: str, 
    user_role: str,
    status_filter: Optional[AppointmentStatusEnum] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Appointment]:
    """Get appointments for a user with filtering"""
    
    query = db.query(Appointment)
    
    # Apply user-specific filters
    if user_role == RoleEnum.PATIENT.value:
        query = query.filter(Appointment.patient_id == user_id)
    elif user_role == RoleEnum.DOCTOR.value:
        query = query.filter(Appointment.doctor_id == user_id)
    else:
        # Admin users can see all appointments
        pass
    
    # Apply status filter
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    
    # Apply date range filter
    if from_date:
        query = query.filter(Appointment.scheduled_datetime >= from_date)
    if to_date:
        query = query.filter(Appointment.scheduled_datetime <= to_date)
    
    # Order by scheduled datetime (most recent first)
    query = query.order_by(desc(Appointment.scheduled_datetime))
    
    return query.offset(offset).limit(limit).all()


def get_upcoming_appointments(db: Session, user_id: str, user_role: str, days_ahead: int = 7) -> List[Appointment]:
    """Get upcoming appointments for next N days"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    future_date = now + timedelta(days=days_ahead)
    
    return get_appointments_for_user(
        db, 
        user_id, 
        user_role,
        from_date=now,
        to_date=future_date,
        status_filter=None
    )


def update_appointment(
    db: Session, 
    appointment_id: str, 
    request: AppointmentUpdateRequest,
    user_id: str,
    user_role: str
) -> Appointment:
    """Update an existing appointment"""
    
    appointment = get_appointment_by_id(db, appointment_id, user_id, user_role)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Update fields that are provided
    if request.scheduled_datetime is not None:
        appointment.scheduled_datetime = request.scheduled_datetime
    if request.duration_minutes is not None:
        appointment.duration_minutes = request.duration_minutes
    if request.appointment_type is not None:
        appointment.appointment_type = request.appointment_type
    if request.status is not None:
        appointment.status = request.status
    if request.title is not None:
        appointment.title = request.title
    if request.description is not None:
        appointment.description = request.description
    if request.location is not None:
        appointment.location = request.location
    if request.is_virtual is not None:
        appointment.is_virtual = request.is_virtual
    if request.virtual_meeting_link is not None:
        appointment.virtual_meeting_link = request.virtual_meeting_link
    
    # Role-based field updates
    if user_role == RoleEnum.DOCTOR.value:
        if request.doctor_notes is not None:
            appointment.doctor_notes = request.doctor_notes
        if request.patient_notes is not None:
            appointment.patient_notes = request.patient_notes
    
    appointment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


def cancel_appointment(db: Session, appointment_id: str, user_id: str, user_role: str) -> Appointment:
    """Cancel an appointment"""
    
    appointment = get_appointment_by_id(db, appointment_id, user_id, user_role)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if appointment.status in [AppointmentStatusEnum.COMPLETED, AppointmentStatusEnum.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status: {appointment.status.value}"
        )
    
    appointment.status = AppointmentStatusEnum.CANCELLED
    appointment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    db.commit()
    db.refresh(appointment)
    
    return appointment


def get_appointment_stats(db: Session, user_id: str, user_role: str) -> AppointmentStatsResponse:
    """Get appointment statistics for a user"""
    
    base_query = db.query(Appointment)
    
    # Apply user-specific filters
    if user_role == RoleEnum.PATIENT.value:
        base_query = base_query.filter(Appointment.patient_id == user_id)
    elif user_role == RoleEnum.DOCTOR.value:
        base_query = base_query.filter(Appointment.doctor_id == user_id)
    
    # Get total count
    total_appointments = base_query.count()
    
    # Get counts by status
    scheduled = base_query.filter(Appointment.status == AppointmentStatusEnum.SCHEDULED).count()
    confirmed = base_query.filter(Appointment.status == AppointmentStatusEnum.CONFIRMED).count()
    completed = base_query.filter(Appointment.status == AppointmentStatusEnum.COMPLETED).count()
    cancelled = base_query.filter(Appointment.status == AppointmentStatusEnum.CANCELLED).count()
    
    # Get upcoming counts
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_end = now.replace(hour=23, minute=59, second=59)
    week_end = now + timedelta(days=7)
    
    upcoming_today = base_query.filter(
        and_(
            Appointment.scheduled_datetime >= now,
            Appointment.scheduled_datetime <= today_end,
            Appointment.status.in_([
                AppointmentStatusEnum.SCHEDULED, 
                AppointmentStatusEnum.CONFIRMED
            ])
        )
    ).count()
    
    upcoming_this_week = base_query.filter(
        and_(
            Appointment.scheduled_datetime >= now,
            Appointment.scheduled_datetime <= week_end,
            Appointment.status.in_([
                AppointmentStatusEnum.SCHEDULED, 
                AppointmentStatusEnum.CONFIRMED
            ])
        )
    ).count()
    
    return AppointmentStatsResponse(
        total_appointments=total_appointments,
        scheduled=scheduled,
        confirmed=confirmed,
        completed=completed,
        cancelled=cancelled,
        upcoming_today=upcoming_today,
        upcoming_this_week=upcoming_this_week
    )


def to_appointment_response(appointment: Appointment) -> AppointmentResponse:
    """Convert Appointment model to AppointmentResponse"""
    return AppointmentResponse(
        appointment_id=appointment.appointment_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        patient_name=appointment.patient.full_name if appointment.patient else "Unknown",
        doctor_name=appointment.doctor.full_name if appointment.doctor else "Unknown",
        scheduled_datetime=appointment.scheduled_datetime,
        duration_minutes=appointment.duration_minutes,
        appointment_type=appointment.appointment_type,
        status=appointment.status,
        title=appointment.title,
        description=appointment.description,
        location=appointment.location,
        is_virtual=appointment.is_virtual,
        virtual_meeting_link=appointment.virtual_meeting_link,
        doctor_notes=appointment.doctor_notes,
        patient_notes=appointment.patient_notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )