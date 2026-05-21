import json
import logging
import os
import re
import sys
from typing import Any, Dict

from dotenv import load_dotenv
import google.generativeai as genai


# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# CUSTOM EXCEPTIONS
# =========================================================

class GeminiServiceError(Exception):

    def __init__(
        self,
        message: str,
        step: str | None = None,
        details: str | None = None,
    ) -> None:

        super().__init__(message)

        self.step = step
        self.details = details


class GeminiQuotaExceededError(
    GeminiServiceError
):

    def __init__(
        self,
        message: str,
        retry_after_seconds: int | None = None,
    ) -> None:

        super().__init__(
            message,
            step="gemini_generate_content"
        )

        self.retry_after_seconds = (
            retry_after_seconds
        )


# =========================================================
# GEMINI SERVICE
# =========================================================

class GeminiService:

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-3.5-flash"
    ) -> None:

        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        self.model_name = model_name

        if not self.api_key:

            raise GeminiServiceError(
                "GEMINI_API_KEY is missing",
                step="gemini_config"
            )

        try:

            logger.info("=" * 80)
            logger.info(
                "INITIALIZING GEMINI MODEL"
            )

            logger.info(
                f"MODEL NAME: {self.model_name}"
            )

            genai.configure(
                api_key=self.api_key
            )

            self.model = (
                genai.GenerativeModel(
                    self.model_name
                )
            )

            logger.info(
                "GEMINI INITIALIZED SUCCESSFULLY"
            )

            logger.info("=" * 80)

            sys.stdout.flush()

        except Exception as exc:

            logger.exception(
                "GEMINI INITIALIZATION FAILED"
            )

            raise GeminiServiceError(
                f"Could not initialize Gemini model: {exc}",
                step="gemini_init"
            ) from exc

    # =====================================================
    # MAIN FUNCTION
    # =====================================================

    def analyze_email(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        logger.info("=" * 80)
        logger.info("STEP build_prompt start")

        prompt = self._build_prompt(
            payload
        )

        logger.info("STEP build_prompt success")

        logger.info("=" * 80)

        logger.info(
            "FINAL PROMPT SENT TO GEMINI"
        )

        logger.info(prompt)

        logger.info("=" * 80)

        sys.stdout.flush()

        try:

            logger.info(
                "STEP generate_content start"
            )

            generation_config = (
                genai.GenerationConfig(
                    temperature=0.2,
                    top_p=0.8,
                    max_output_tokens=3000,
                    response_mime_type="application/json",
                )
            )

            logger.info(
                f"GENERATION CONFIG: {generation_config}"
            )

            response = (
                self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    request_options={
                        "timeout": 30
                    }
                )
            )

            logger.info(
                "STEP generate_content success"
            )

            logger.info(
                f"RESPONSE TYPE: {type(response)}"
            )

            logger.info("=" * 80)
            logger.info("RAW RESPONSE OBJECT")
            logger.info(response)
            logger.info("=" * 80)

            sys.stdout.flush()

            # =================================================
            # EXTRACT RAW TEXT
            # =================================================

            generated_text = (
                self._extract_text(
                    response
                )
            )

            logger.info("=" * 80)
            logger.info(
                "RAW GEMINI RESPONSE"
            )
            logger.info(generated_text)
            logger.info("=" * 80)

            sys.stdout.flush()

            if not generated_text:

                raise GeminiServiceError(
                    "Gemini returned empty response",
                    step="empty_response"
                )

            # =================================================
            # CHECK FOR INCOMPLETE JSON
            # =================================================

            if not generated_text.strip().endswith("}"):

                logger.error(
                    "INCOMPLETE JSON DETECTED"
                )

                raise GeminiServiceError(
                    "Gemini returned incomplete JSON due to token truncation",
                    step="json_truncation",
                    details=generated_text
                )

            # =================================================
            # CLEAN RESPONSE
            # =================================================

            repaired_text = (
                self._repair_json(
                    generated_text
                )
            )

            logger.info("=" * 80)
            logger.info(
                "REPAIRED JSON RESPONSE"
            )
            logger.info(repaired_text)
            logger.info("=" * 80)

            sys.stdout.flush()

            # =================================================
            # JSON PARSE
            # =================================================

            try:

                parsed_json = json.loads(
                    repaired_text
                )

            except json.JSONDecodeError as exc:

                logger.exception(
                    "JSON PARSE FAILED"
                )

                raise GeminiServiceError(
                    f"Invalid JSON returned by Gemini: {exc}",
                    step="json_parse",
                    details=repaired_text
                ) from exc

            logger.info("=" * 80)
            logger.info(
                "FINAL PARSED JSON"
            )
            logger.info(parsed_json)
            logger.info("=" * 80)

            sys.stdout.flush()

            return (
                self._validate_output_schema(
                    parsed_json,
                    payload
                )
            )

        except Exception as exc:

            logger.exception(
                "GEMINI ANALYSIS FAILED"
            )

            error_message = str(exc)

            logger.error("=" * 80)
            logger.error(
                f"FINAL ERROR: {error_message}"
            )
            logger.error(
                f"STEP: {getattr(exc, 'step', None)}"
            )
            logger.error("=" * 80)

            sys.stdout.flush()

            if (
                self._is_quota_or_rate_limit_error(
                    error_message
                )
            ):

                raise (
                    GeminiQuotaExceededError(
                        (
                            "Gemini quota exceeded: "
                            f"{exc}"
                        ),
                        retry_after_seconds=(
                            self
                            ._extract_retry_after_seconds(
                                error_message
                            )
                        )
                    )
                ) from exc

            raise GeminiServiceError(
                f"Gemini analysis failed: {exc}",
                step=getattr(exc, "step", None),
                details=error_message,
            ) from exc

    # =====================================================
    # PROMPT BUILDER
    # =====================================================

    def _build_prompt(
        self,
        payload: Dict[str, Any]
    ) -> str:

        email_data = payload.get(
            "email",
            {}
        )

        user_data = payload.get(
            "user",
            {}
        )

        email_id = email_data.get(
            "email_id",
            ""
        )

        sender = email_data.get(
            "sender",
            ""
        )

        subject = email_data.get(
            "subject",
            ""
        )

        body = email_data.get(
            "body",
            ""
        )

        # =================================================
        # MINIMAL CONTEXT
        # =================================================

        minimal_context = {
            "name": user_data.get("name"),
            "position": user_data.get("position"),
            "organization": user_data.get("organization"),
            "preferredTone": user_data.get("preferredTone"),
        }

        user_context = json.dumps(
            minimal_context,
            ensure_ascii=False,
            indent=2
        )

        email_content = (
            f"Sender: {sender}\n"
            f"Subject: {subject}\n\n"
            f"{body}"
        ).strip()

        return f"""
You are an AI email assistant.

Return ONLY valid JSON.

STRICT FORMAT:

{{
  "category": "replyable",
  "email_id": "{email_id}",
  "summary": "...",
  "reply_draft": "...",
  "signature": false
}}

RULES:
- Keep summary under 30 words
- Keep reply_draft under 120 words
- Escape all newlines using \\n
- No markdown
- No code blocks
- No triple backticks
- Close all quotes properly
- Always return complete JSON

CATEGORY RULES:
- spam
- replyable
- ignorable

EMAIL:
{email_content}

USER CONTEXT:
{user_context}
""".strip()

    # =====================================================
    # EXTRACT RESPONSE TEXT
    # =====================================================

    @staticmethod
    def _extract_text(
        response: Any
    ) -> str:

        try:

            if hasattr(response, "text"):

                return str(
                    response.text
                ).strip()

            return ""

        except Exception:

            return ""

    # =====================================================
    # CLEAN / REPAIR JSON
    # =====================================================

    @staticmethod
    def _repair_json(
        text: str
    ) -> str:

        cleaned = text.strip()

        cleaned = cleaned.replace(
            "```json",
            ""
        )

        cleaned = cleaned.replace(
            "```",
            ""
        )

        cleaned = cleaned.replace(
            "\r",
            ""
        )

        return cleaned.strip()

    # =====================================================
    # VALIDATE OUTPUT
    # =====================================================

    @staticmethod
    def _validate_output_schema(
        parsed: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        logger.info("=" * 80)
        logger.info(
            "SCHEMA VALIDATION START"
        )
        logger.info(parsed)
        logger.info("=" * 80)

        required_fields = [
            "category",
            "email_id",
            "summary",
            "reply_draft",
            "signature",
        ]

        for field in required_fields:

            if field not in parsed:

                raise GeminiServiceError(
                    f"Missing field: {field}",
                    step="schema_validation"
                )

        category = parsed.get(
            "category"
        )

        valid_categories = {
            "spam",
            "replyable",
            "ignorable"
        }

        if category not in valid_categories:

            raise GeminiServiceError(
                f"Invalid category: {category}",
                step="schema_validation"
            )

        logger.info(
            "SCHEMA VALIDATION SUCCESS"
        )

        return parsed

    # =====================================================
    # QUOTA CHECK
    # =====================================================

    @staticmethod
    def _is_quota_or_rate_limit_error(
        error_message: str
    ) -> bool:

        lowered = error_message.lower()

        return any(
            token in lowered
            for token in [
                "429",
                "quota exceeded",
                "rate limit",
                "retry in",
                "free_tier_requests",
            ]
        )

    # =====================================================
    # RETRY DELAY
    # =====================================================

    @staticmethod
    def _extract_retry_after_seconds(
        error_message: str
    ) -> int | None:

        match = re.search(
            r"Please retry in ([0-9]+(?:\.[0-9]+)?)s",
            error_message
        )

        if match:

            return max(
                1,
                int(float(match.group(1)))
            )

        return None