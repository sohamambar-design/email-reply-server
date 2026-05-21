import logging
import math
import re

from flask import Blueprint, jsonify, request

from services.gemini_service import (
    GeminiQuotaExceededError,
    GeminiService,
    GeminiServiceError,
)
from utils.validators import validate_generate_reply_payload


logger = logging.getLogger(__name__)
email_bp = Blueprint("email", __name__)


def _build_error_response(exc: Exception, default_error: str, status_code: int, extra: dict | None = None):
    payload = {
        "success": False,
        "error": default_error,
        "details": str(exc),
    }

    step = getattr(exc, "step", None)
    if step:
        payload["error_step"] = step

    details = getattr(exc, "details", None)
    if details:
        payload["debug_details"] = details

    if extra:
        payload.update(extra)

    return jsonify(payload), status_code


def _extract_retry_after_seconds(error_message: str) -> int | None:
    """Extract Gemini retry delay from an error message if present."""
    match = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", error_message)
    if match:
        return max(1, math.ceil(float(match.group(1))))

    match = re.search(r"retry_delay\s*[:=]\s*([0-9]+)", error_message, flags=re.IGNORECASE)
    if match:
        return max(1, int(match.group(1)))

    return None


def _is_quota_or_rate_limit_error(error_message: str) -> bool:
    lowered = error_message.lower()
    return any(
        token in lowered
        for token in [
            "429",
            "quota exceeded",
            "rate limit",
            "rate-limits",
            "retry in",
            "free_tier_requests",
        ]
    )


@email_bp.route("/health", methods=["GET"])
def health_check():
    """Simple health endpoint to verify service is running."""
    return jsonify({"success": True, "message": "Smart Email Reply Agent backend is running"}), 200


@email_bp.route("/generate-reply", methods=["POST"])
def generate_reply():
    """Classify an email and return the structured JSON response from Gemini."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Content-Type must be application/json", "error_step": "request_validation"}), 415

    payload = request.get_json(silent=True)
    is_valid, errors, normalized_payload = validate_generate_reply_payload(payload)

    if not is_valid:
        return jsonify({"success": False, "error": "Validation failed", "details": errors, "error_step": "payload_validation"}), 400

    email_id = normalized_payload["email_id"]

    try:
        gemini_service = GeminiService()
        structured_response = gemini_service.analyze_email(normalized_payload)
        return jsonify(structured_response), 200
    except GeminiServiceError as exc:
        logger.exception("Gemini service error while generating reply for email_id=%s", email_id)

        if isinstance(exc, GeminiQuotaExceededError):
            return _build_error_response(
                exc,
                "Gemini quota exceeded",
                429,
                extra={
                    "retry_after_seconds": exc.retry_after_seconds,
                } if exc.retry_after_seconds is not None else None,
            )

        error_message = str(exc)

        if "GEMINI_API_KEY" in error_message:
            return jsonify({
                "success": False,
                "error": "Server configuration error",
                "details": "GEMINI_API_KEY is not configured",
                "error_step": getattr(exc, "step", "gemini_config"),
            }), 500

        return _build_error_response(exc, "Failed to generate reply", 502)
    except Exception:
        logger.exception("Unexpected error while generating reply for email_id=%s", email_id)
        return jsonify({"success": False, "error": "Internal server error", "error_step": "unexpected_exception"}), 500
