"""
Enhanced Events Controller with Multi-Tenancy Support
Handles event filtering based on organization for Smart Guard system
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from database import get_db
from models import Event, User
from schemas import EventResponse
from auth import get_current_user

security = HTTPBearer()

@router.get("/events", response_model=List[EventResponse])
async def get_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    organization_id: Optional[str] = None
):
    """
    Get events with organization-based filtering
    
    - Smart Guard (admin@smartguard.com): Can filter by organization or see all if no filter specified
    - Regular Admins: Can only see events from their own organization
    - Regular Users: Can only see events from their own organization
    """
    try:
        query = db.query(Event)
        
        # Check if user is Smart Guard (super admin)
        is_smart_guard = current_user.email == "admin@smartguard.com"
        
        # Apply organization filtering based on user role
        if is_smart_guard:
            # Smart Guard can filter by specific organization or see all
            if organization_id:
                try:
                    org_uuid = uuid.UUID(organization_id)
                    query = query.filter(Event.org_id == org_uuid)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid organization ID format"
                    )
        else:
            # All other users (including regular admins) only see their organization's events
            query = query.filter(Event.org_id == current_user.org_id)
        
        # Apply pagination
        events = query.offset(skip).limit(limit).all()
        
        return events
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching events: {str(e)}"
        )

@router.post("/events", response_model=EventResponse)
async def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new event with automatic organization assignment
    """
    try:
        # Automatically set org_id based on current user
        event_data = event.dict()
        event_data['org_id'] = current_user.org_id
        event_data['created_by'] = current_user.id
        
        new_event = Event(**event_data)
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        
        return new_event
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating event: {str(e)}"
        )

@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific event with organization access check
    Only Smart Guard can access events from any organization
    """
    try:
        event_uuid = uuid.UUID(event_id)
        event = db.query(Event).filter(Event.id == event_uuid).first()
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )
        
        # Check if user is Smart Guard (super admin)
        is_smart_guard = current_user.email == "admin@smartguard.com"
        
        # Check organization access (only Smart Guard can access all organizations)
        if not is_smart_guard and event.org_id != current_user.org_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access events from your organization"
            )
        
        return event
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid event ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching event: {str(e)}"
        )
