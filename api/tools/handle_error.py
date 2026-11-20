from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError


def json_response(content, status=200):
    """
    Legacy JSON response wrapper
    Use Pydantic response_model instead, it handles JSON serialization automatically
    """
    response = JSONResponse(
        status_code=status,
        content=jsonable_encoder(content),
        media_type="application/json",
    )
    return response


def json_response_message(message):
    body = {"message": message, "error": 0}
    return json_response(body)


def json_response_error(message):
    body = {"message": message, "error": 1}
    return json_response(body, status=422)


def kucoin_rate_limit_detail(error: Exception) -> str | None:
    code = getattr(error, "code", None)
    message = getattr(error, "message", None)
    if str(code) == "429000":
        return f"Kucoin {code} {message or 'Too many requests'}"

    error_text = str(error)
    if "429000" in error_text:
        message_text = (
            "Too many requests" if "Too many requests" in error_text else error_text
        )
        return f"Kucoin 429000 {message_text}"

    return None


def format_db_error(e: SQLAlchemyError) -> str:
    if isinstance(e, IntegrityError):
        return "Database integrity constraint violated"
    if isinstance(e, DataError):
        return "Invalid or out-of-range data for database column"
    return f"Database error: {e.__class__.__name__}"
