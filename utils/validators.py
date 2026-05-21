import re
from typing import Any, Dict, List, Tuple

# =========================
# Constants
# =========================

EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

VALID_TONES = {
    "professional",
    "friendly",
    "formal",
    "neutral",
    "concise"
}

MAX_TEXT_LENGTH = 50000


# =========================
# Sanitization Helpers
# =========================

def sanitize_text(value: str) -> str:
    """
    Remove unsafe control characters and trim spaces.
    """
    cleaned = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
        "",
        value
    )
    return cleaned.strip()


def sanitize_payload(payload: Any) -> Any:
    """
    Recursively sanitize incoming JSON payload.
    """

    if isinstance(payload, str):
        return sanitize_text(payload)

    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]

    if isinstance(payload, dict):
        return {
            key: sanitize_payload(value)
            for key, value in payload.items()
        }

    return payload


# =========================
# Validation Helpers
# =========================

def validate_string_length(
    field_name: str,
    value: str,
    errors: List[str]
) -> None:

    if len(value) > MAX_TEXT_LENGTH:
        errors.append(
            f"{field_name} exceeds "
            f"{MAX_TEXT_LENGTH} characters"
        )


def validate_required_fields(
    payload: Dict[str, Any],
    errors: List[str]
) -> None:

    if "email" not in payload:
        errors.append("Missing required field: email")

    if "user" not in payload:
        errors.append("Missing required field: user")


# =========================
# Email Validation
# =========================

def validate_email_block(
    email_data: Dict[str, Any],
    errors: List[str]
) -> Dict[str, Any]:

    required_fields = [
        "email_id",
        "sender",
        "subject",
        "body"
    ]

    for field in required_fields:
        if field not in email_data:
            errors.append(
                f"Missing required email field: {field}"
            )

    email_id = sanitize_text(
        str(email_data.get("email_id", ""))
    )

    sender = sanitize_text(
        str(email_data.get("sender", ""))
    )

    subject = sanitize_text(
        str(email_data.get("subject", ""))
    )

    body = sanitize_text(
        str(email_data.get("body", ""))
    )

    # Empty validations
    if not email_id:
        errors.append("email.email_id cannot be empty")

    if not sender:
        errors.append("email.sender cannot be empty")

    if not subject:
        errors.append("email.subject cannot be empty")

    if not body:
        errors.append("email.body cannot be empty")

    # Email format validation
    if sender and not EMAIL_REGEX.match(sender):
        errors.append("Invalid sender email format")

    # Length validation
    validate_string_length(
        "email.subject",
        subject,
        errors
    )

    validate_string_length(
        "email.body",
        body,
        errors
    )

    return {
        "email_id": email_id,
        "sender": sender,
        "subject": subject,
        "body": body
    }


# =========================
# User Validation
# =========================

def validate_user_block(
    user_data: Dict[str, Any],
    errors: List[str]
) -> Dict[str, Any]:

    required_user_fields = [
        "name",
        "email"
    ]

    for field in required_user_fields:
        value = str(
            user_data.get(field, "")
        ).strip()

        if not value:
            errors.append(
                f"user.{field} cannot be empty"
            )

    user_email = sanitize_text(
        str(user_data.get("email", ""))
    )

    if user_email and not EMAIL_REGEX.match(user_email):
        errors.append(
            "Invalid user email format"
        )

    tone_value = user_data.get(
        "preferredTone",
        "professional"
    )

    tone = sanitize_text(
        str(tone_value).lower()
    )

    if tone not in VALID_TONES:
        tone = "professional"

    # Lists
    information = user_data.get("information", [])
    calendar_events = user_data.get("calendarEvents", [])
    important_contacts = user_data.get("importantContacts", [])
    call_history = user_data.get("callHistory", [])

    # Type validation
    list_fields = {
        "information": information,
        "calendarEvents": calendar_events,
        "importantContacts": important_contacts,
        "callHistory": call_history
    }

    for field_name, value in list_fields.items():

        if value and not isinstance(value, list):
            errors.append(
                f"user.{field_name} must be a list"
            )

    # Validate call history structure
    if isinstance(call_history, list):

        for idx, call in enumerate(call_history):

            if not isinstance(call, dict):
                errors.append(
                    f"callHistory[{idx}] must be an object"
                )
                continue

            if "conversation" not in call:
                errors.append(
                    f"callHistory[{idx}] missing conversation"
                )

    return {
        "user_document_id": sanitize_text(
            str(user_data.get(
                "user_document_id",
                ""
            ))
        ),

        "name": sanitize_text(
            str(user_data.get("name", ""))
        ),

        "email": user_email,

        "phone": sanitize_text(
            str(user_data.get("phone", ""))
        ),

        "position": sanitize_text(
            str(user_data.get("position", ""))
        ),

        "organization": sanitize_text(
            str(user_data.get("organization", ""))
        ),

        "employmentStatus": sanitize_text(
            str(user_data.get(
                "employmentStatus",
                ""
            ))
        ),

        "preferredTone": tone,

        "information": sanitize_payload(information),

        "calendarEvents": sanitize_payload(
            calendar_events
        ),

        "importantContacts": sanitize_payload(
            important_contacts
        ),

        "callHistory": sanitize_payload(
            call_history
        )
    }


# =========================
# Main Validator
# =========================

def validate_generate_reply_payload(
    payload: Any
) -> Tuple[bool, List[str], Dict[str, Any]]:

    errors: List[str] = []

    if payload is None:
        return (
            False,
            ["Request body is empty"],
            {}
        )

    if not isinstance(payload, dict):
        return (
            False,
            ["Payload must be a JSON object"],
            {}
        )

    payload = sanitize_payload(payload)

    validate_required_fields(
        payload,
        errors
    )

    if errors:
        return False, errors, {}

    email_data = payload.get("email", {})
    user_data = payload.get("user", {})

    if not isinstance(email_data, dict):
        errors.append(
            "email must be a JSON object"
        )

    if not isinstance(user_data, dict):
        errors.append(
            "user must be a JSON object"
        )

    if errors:
        return False, errors, {}

    normalized_email = validate_email_block(
        email_data,
        errors
    )

    normalized_user = validate_user_block(
        user_data,
        errors
    )

    normalized_payload = {
        "email_id": normalized_email["email_id"],
        "email": normalized_email,
        "user": normalized_user
    }

    return (
        len(errors) == 0,
        errors,
        normalized_payload
    )