import json
from typing import Any, Union, Optional
from bson import json_util
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.encoders import jsonable_encoder
from copy import deepcopy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError


"""
All below functions should be deprecated
- json_response, json_response_* functions should use default dict or a Pydantic model
- encode_json shouldn't be needed as FastAPI internally does it once json_response_* removed
- IResponseBase duplicate of StandardResponse which has migrated to pybinbot.models.routes. Replace all usage of it by StandardResponse.
"""


def api_response(detail: str, data: Any = None, error: Union[str, int] = 0, status=200):
    """
    Custom Fast API response

    Args:
    - detail: the message of the response
    - data: Pydantic model returned
    """
    body = {"message": detail}
    if data:
        body["data"] = data

    if error:
        body["error"] = str(error)

    return JSONResponse(
        status_code=status,
        content=body,
    )


def json_response(content, status=200):
    """
    Legacy JSON response wrapper
    Use Pydantic response_model instead, it handles JSON serialization automatically
    """
    content = json.loads(json_util.dumps(content))  # Objectid serialization
    response = JSONResponse(
        status_code=status,
        content=content,
        media_type="application/json",
    )
    return response


def json_response_message(message):
    body = {"message": message, "error": 0}
    return json_response(body)


def json_response_error(message):
    body = {"message": message, "error": 1}
    return json_response(body, status=422)


def encode_json(raw):
    """
    Wrapper for jsonable_encoder to encode ObjectId
    """
    if hasattr(raw, "_id"):
        # Objectid serialization
        id = str(raw._id)
        content = deepcopy(raw)
        del content._id
        content = jsonable_encoder(content)
        content["_id"] = id
    else:
        content = jsonable_encoder(raw)
    return content


class IResponseBase(BaseModel):
    message: str
    error: Optional[int] = Field(default=0)


def format_db_error(e: SQLAlchemyError) -> str:
    if isinstance(e, IntegrityError):
        return "Database integrity constraint violated"
    if isinstance(e, DataError):
        return "Invalid or out-of-range data for database column"
    return f"Database error: {e.__class__.__name__}"
