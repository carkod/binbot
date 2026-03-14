from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import Session
from databases.utils import get_session
from databases.crud.inquiry_crud import InquiryCrud
from inquiries.models import InquiryBase, InquiryResponse, InquiryListResponse
from uuid import UUID

inquiries_router = APIRouter(tags=["inquiries"])


@inquiries_router.post("/inquiries", response_model=InquiryResponse)
def create_inquiry(payload: InquiryBase, session: Session = Depends(get_session)):
    crud = InquiryCrud(session)
    try:
        inquiry = crud.create_inquiry(inquiry=payload)
        return {
            "message": "Inquiry created successfully",
            "data": inquiry,
            "error": 0,
        }
    except ValidationError as error:
        raise HTTPException(status_code=400, detail=str(error))


@inquiries_router.get("/inquiries/{id}", response_model=InquiryResponse)
def get_inquiry(id: str, session: Session = Depends(get_session)):
    try:
        sanitized_id = UUID(id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid UUID format.")
    crud = InquiryCrud(session)
    inquiry = crud.get_inquiry(sanitized_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return {
        "message": "Inquiry retrieved successfully",
        "data": inquiry,
        "error": 0,
    }


@inquiries_router.get("/inquiries", response_model=InquiryListResponse)
def get_inquiries(
    offset: int = 0,
    limit: int = 100,
    reason: str | None = Query(default=None, description="Filter inquiries by reason"),
    session: Session = Depends(get_session),
):
    crud = InquiryCrud(session)
    response = crud.get_inquiries(offset=offset, limit=limit, reason=reason)

    return {
        "message": "Inquiries retrieved successfully",
        "data": response,
        "error": 0,
    }


@inquiries_router.delete("/inquiries/{id}", response_model=InquiryResponse)
def delete_inquiry(id: str, session: Session = Depends(get_session)):
    try:
        sanitized_id = UUID(id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid UUID format.")
    crud = InquiryCrud(session)
    inquiry = crud.get_inquiry(sanitized_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    crud.delete_inquiry(sanitized_id)
    return {
        "message": "Inquiry deleted successfully",
        "data": inquiry,  # Return the full inquiry object
        "error": 0,
    }
