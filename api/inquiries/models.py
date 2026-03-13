from uuid import UUID, uuid4
from pydantic import BaseModel, EmailStr, Field, field_validator
from pybinbot import StandardResponse
from databases.tables.inquiry_table import InquiryTable


class InquiryBase(BaseModel):
    full_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    organisation: str = Field(...)
    reason: str = Field(...)
    message: str = Field(default="")
    newsletter: bool = Field(default=False)
    terms_agreement: bool = Field(default=True)

    @field_validator("phone")
    def validate_phone(cls, v):
        if v is not None:
            import re

            if not re.fullmatch(r"^\+?\d{7,15}$", v):
                raise ValueError(
                    "Phone number must be numeric, 7-15 digits, and may start with '+'"
                )
        return v

    @field_validator("full_name", "organisation", "reason", "message")
    def sanitize_strings(cls, v, info):
        if v is not None:
            import re

            v = v.strip()
            if info.field_name == "full_name":
                v = re.sub(r"[^a-zA-Z\s\-']", "", v)
                if not v:
                    raise ValueError("Full name must contain valid characters.")
            elif info.field_name in ("organisation", "reason"):
                v = re.sub(r"[^a-zA-Z0-9\s\-']", "", v)
            elif info.field_name == "message":
                v = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", v)
        return v


class InquiryCreate(InquiryBase):
    id: UUID = Field(default_factory=uuid4)


class InquiryResponse(StandardResponse):
    data: InquiryCreate


class InquiryListResponse(StandardResponse):
    data: list[InquiryTable]
