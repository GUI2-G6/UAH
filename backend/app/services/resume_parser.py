import asyncio
import re
import json
import base64
import logging
from io import BytesIO
from pathlib import Path
import tempfile
from datetime import datetime, timedelta, timezone
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_PARSE_METHODS = ("cloud", "local", "rules")
LOCAL_PIPELINE_UNAVAILABLE_MESSAGE = "Local AI is unavailable right now."
LOCAL_PIPELINE_PROBE_TIMEOUT_SECONDS = 1.5
_CLOUD_DEGRADED_UNTIL: datetime | None = None
_CLOUD_DEGRADED_MESSAGE: str | None = None
_CLOUD_DEGRADED_TTL_SECONDS = 300
_TRANSIENT_CLOUD_PARSE_ERROR_CODES = {
    "CLOUD_OCR_RATE_LIMITED",
    "CLOUD_OCR_PROVIDER_BUSY",
    "CLOUD_OCR_PROVIDER_UNAVAILABLE",
    "CLOUD_OCR_TIMEOUT",
    "CLOUD_OCR_REQUEST_FAILED",
    "CLOUD_LLM_RATE_LIMITED",
    "CLOUD_LLM_PROVIDER_BUSY",
    "CLOUD_LLM_PROVIDER_UNAVAILABLE",
    "CLOUD_LLM_TIMEOUT",
    "CLOUD_LLM_REQUEST_FAILED",
}
_TERMINAL_CLOUD_PARSE_ERROR_CODES = {
    "CLOUD_OCR_QUOTA_EXHAUSTED",
    "CLOUD_LLM_QUOTA_EXHAUSTED",
}
PLACEHOLDER_VALUES = {
    "null",
    "none",
    "n/a",
    "na",
    "unknown",
    "not provided",
    "not available",
    "-",
    "--",
}

PORTAL_REQUIRED_FIELDS = {
    "personal_info.first_name": "First Name",
    "personal_info.last_name": "Last Name",
    "personal_info.email": "Email",
    "personal_info.phone": "Phone",
    "personal_info.city": "City",
    "personal_info.state": "State",
    "education[0].institution": "School / University",
    "education[0].degree": "Degree",
    "education[0].field_of_study": "Field of Study",
    "education[0].start_date": "Education Start Date",
    "education[0].end_date": "Education End Date",
    "work_experience[0].company": "Employer",
    "work_experience[0].title": "Job Title",
    "work_experience[0].start_date": "Work Start Date",
    "work_experience[0].end_date": "Work End Date",
}

CATEGORIZE_PROMPT = """You are an expert resume parser. Given the following OCR-extracted resume text (in markdown format), extract ALL information into the exact JSON schema below.

CRITICAL RULES:
1. REQUIRED FIELDS (job portals will reject applications without these):
   - personal_info: first_name, last_name, email, phone, city, state
   - education (first entry): institution, degree, field_of_study, start_date, end_date
   - work_experience (first entry): company, title, start_date, end_date
   Try EXTREMELY hard to fill these. Infer from context clues:
   - Name: check email user parts, headers, footers, signatures.
   - City/State: check addresses, university locations, employer locations.
   - Dates: if only a year is given, use "January YYYY" for start and "December YYYY" for end.
   - If a date range uses a dash like "2020-2023", expand to "January 2020" - "December 2023".

2. GENERAL RULES:
   - Be thorough. Do not skip any information found in the text.
   - If a field is truly not found, use null for strings and [] for arrays.
   - Normalize all dates to "Month YYYY" format (e.g., "Sept 2023" -> "September 2023"). Use "Present" for current positions.
   - Split full names into first_name and last_name.
   - For GPA, extract as a string like "3.46/4.00".
   - For skills, categorize them into the appropriate sub-arrays.
   - Extract ALL bullet points for each work experience and project entry.
   - For location fields, if only a city is found, still populate city. If a US state abbreviation is found (e.g. "MA"), put it in state.

JSON Schema (return ONLY valid JSON, no markdown fences, no explanation):
{
  "personal_info": {
    "first_name": "",
    "last_name": "",
    "email": "",
    "phone": "",
    "address": "",
    "city": "",
    "state": "",
    "zip": "",
    "linkedin": "",
    "website": ""
  },
  "summary": "",
  "education": [
    {
      "institution": "",
      "degree": "",
      "field_of_study": "",
      "gpa": "",
      "start_date": "",
      "end_date": "",
      "honors": [],
      "relevant_coursework": []
    }
  ],
  "work_experience": [
    {
      "company": "",
      "title": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "is_current": false,
      "bullets": []
    }
  ],
  "skills": {
    "technical": [],
    "languages": [],
    "tools": [],
    "soft_skills": []
  },
  "projects": [
    {
      "name": "",
      "description": "",
      "technologies": [],
      "date": ""
    }
  ],
  "certifications": [
    {
      "name": "",
      "issuer": "",
      "date": ""
    }
  ],
  "awards": [],
  "activities": [],
  "volunteer": []
}

Resume Text:
"""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _trim_text(value: str | None, limit: int = 200) -> str:
    return (value or "").strip()[:limit]


def _extract_retry_after_seconds(headers: httpx.Headers | None) -> int | None:
    if headers is None:
        return None
    raw = (headers.get("Retry-After") or "").strip()
    if not raw:
        return None
    try:
        return max(int(float(raw)), 0)
    except Exception:
        return None


def _parse_provider_payload(resp: httpx.Response) -> dict:
    try:
        payload = resp.json()
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _provider_message(payload: dict, fallback: str) -> str:
    for key in ("message", "msg", "error_msg", "errorMessage", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    error = payload.get("error")
    if isinstance(error, dict):
        for key in ("message", "msg", "detail"):
            value = error.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(error, str) and error.strip():
        return error.strip()
    return fallback


def _provider_code(payload: dict) -> str:
    for key in ("code", "error_code", "errorCode", "type"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    error = payload.get("error")
    if isinstance(error, dict):
        for key in ("code", "type"):
            value = error.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return ""


def _looks_like_quota_limit(code: str, message: str) -> bool:
    combined = f"{code} {message}".lower()
    hard_limit_markers = (
        "quota",
        "balance",
        "insufficient",
        "billing",
        "payment",
        "fair use",
        "fair-use",
        "subscription",
        "plan limit",
        "daily limit",
        "weekly limit",
        "monthly limit",
        "account limit",
        "usage limit",
    )
    return any(marker in combined for marker in hard_limit_markers)


def _looks_like_transient_rate_limit(code: str, message: str) -> bool:
    combined = f"{code} {message}".lower()
    transient_markers = (
        "rate",
        "throttle",
        "concurr",
        "frequency",
        "too many",
        "busy",
        "capacity",
    )
    return any(marker in combined for marker in transient_markers)


def _set_cloud_degraded(message: str | None) -> None:
    global _CLOUD_DEGRADED_UNTIL, _CLOUD_DEGRADED_MESSAGE
    _CLOUD_DEGRADED_UNTIL = _now_utc() + timedelta(seconds=_CLOUD_DEGRADED_TTL_SECONDS)
    _CLOUD_DEGRADED_MESSAGE = (message or "").strip() or "Cloud AI is rate limited right now. UAH is retrying with provider-aware backoff."


def _clear_cloud_degraded() -> None:
    global _CLOUD_DEGRADED_UNTIL, _CLOUD_DEGRADED_MESSAGE
    _CLOUD_DEGRADED_UNTIL = None
    _CLOUD_DEGRADED_MESSAGE = None


def get_cloud_provider_availability() -> dict:
    degraded = bool(_CLOUD_DEGRADED_UNTIL and _CLOUD_DEGRADED_UNTIL > _now_utc())
    return {
        "available": True,
        "degraded": degraded,
        "message": _CLOUD_DEGRADED_MESSAGE if degraded else None,
    }


def is_retryable_cloud_parse_error(error_code: str | None) -> bool:
    normalized = (error_code or "").strip().upper()
    return normalized in _TRANSIENT_CLOUD_PARSE_ERROR_CODES


def is_terminal_cloud_parse_error(error_code: str | None) -> bool:
    normalized = (error_code or "").strip().upper()
    return normalized in _TERMINAL_CLOUD_PARSE_ERROR_CODES


def classify_cloud_provider_error(
    stage: str,
    status_code: int,
    payload: dict | None = None,
    response_text: str | None = None,
    retry_after_seconds: int | None = None,
) -> dict:
    payload = payload or {}
    stage_label = "OCR" if stage == "ocr" else "LLM"
    provider_code = _provider_code(payload)
    provider_message = _provider_message(payload, _trim_text(response_text))

    if status_code == 429:
        if _looks_like_quota_limit(provider_code, provider_message):
            return {
                "error_code": f"CLOUD_{stage_label}_QUOTA_EXHAUSTED",
                "message": "Cloud AI quota or usage limits are exhausted right now. Please try again later.",
                "retryable": False,
                "provider_code": provider_code,
                "provider_message": provider_message,
                "retry_after_seconds": retry_after_seconds,
            }
        transient_message = "Cloud AI is temporarily rate limited. UAH will retry automatically." if stage == "llm" else "Cloud OCR is temporarily rate limited. UAH will retry automatically."
        transient_code = f"CLOUD_{stage_label}_RATE_LIMITED"
        if _looks_like_transient_rate_limit(provider_code, provider_message):
            return {
                "error_code": transient_code,
                "message": transient_message,
                "retryable": True,
                "provider_code": provider_code,
                "provider_message": provider_message,
                "retry_after_seconds": retry_after_seconds,
            }
        return {
            "error_code": f"CLOUD_{stage_label}_PROVIDER_BUSY",
            "message": transient_message,
            "retryable": True,
            "provider_code": provider_code,
            "provider_message": provider_message,
            "retry_after_seconds": retry_after_seconds,
        }

    if status_code >= 500:
        return {
            "error_code": f"CLOUD_{stage_label}_PROVIDER_UNAVAILABLE",
            "message": f"Cloud {stage_label.lower()} service is temporarily unavailable. UAH will retry automatically.",
            "retryable": True,
            "provider_code": provider_code,
            "provider_message": provider_message,
            "retry_after_seconds": retry_after_seconds,
        }

    return {
        "error_code": f"CLOUD_{stage_label}_API_ERROR",
        "message": f"Cloud {stage_label.lower()} service returned status {status_code}. Please retry.",
        "retryable": False,
        "provider_code": provider_code,
        "provider_message": provider_message,
        "retry_after_seconds": retry_after_seconds,
    }


async def ocr_pdf(pdf_bytes: bytes) -> dict:
    missing = settings.missing_resume_ocr_config()
    if missing:
        logger.error("OCR is not configured. Missing env vars: %s", ", ".join(missing))
        return {
            "ok": False,
            "error_code": "OCR_NOT_CONFIGURED",
            "status_code": 503,
            "response_excerpt": f"Missing config: {', '.join(missing)}",
        }

    file_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    data_url = f"data:application/pdf;base64,{file_base64}"

    request_body = {
        "model": "glm-ocr",
        "file": data_url,
        "return_crop_images": False,
        "need_layout_visualization": True,
    }
    headers = {
        "Authorization": f"Bearer {settings.ZAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(settings.ZAI_OCR_URL, json=request_body, headers=headers)

        if resp.status_code != 200:
            payload = _parse_provider_payload(resp)
            classified = classify_cloud_provider_error(
                stage="ocr",
                status_code=resp.status_code,
                payload=payload,
                response_text=resp.text,
                retry_after_seconds=_extract_retry_after_seconds(resp.headers),
            )
            if classified.get("retryable"):
                _set_cloud_degraded(classified.get("message"))
            logger.error(
                f"OCR API error: status={resp.status_code}, url={settings.ZAI_OCR_URL}, "
                f"response_text={resp.text[:200]}"
            )
            return {
                "ok": False,
                "error_code": classified["error_code"],
                "status_code": resp.status_code,
                "response_excerpt": (resp.text or "")[:200],
                "message": classified["message"],
                "retryable": classified.get("retryable", False),
                "retry_after_seconds": classified.get("retry_after_seconds"),
                "provider_code": classified.get("provider_code"),
                "provider_message": classified.get("provider_message"),
            }

        payload = resp.json()
        payload["ok"] = True
        _clear_cloud_degraded()
        return payload
    except httpx.TimeoutException as e:
        logger.error("OCR request timed out: %s", str(e))
        _set_cloud_degraded("Cloud OCR timed out. UAH will retry automatically.")
        return {
            "ok": False,
            "error_code": "CLOUD_OCR_TIMEOUT",
            "status_code": 504,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "message": "Cloud OCR timed out. UAH will retry automatically.",
            "retryable": True,
        }
    except httpx.HTTPError as e:
        logger.error("OCR request failed: %s: %s", type(e).__name__, str(e))
        _set_cloud_degraded("Cloud OCR could not be reached. UAH will retry automatically.")
        return {
            "ok": False,
            "error_code": "CLOUD_OCR_REQUEST_FAILED",
            "status_code": 502,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "message": "Cloud OCR could not be reached. UAH will retry automatically.",
            "retryable": True,
        }
    except Exception as e:
        logger.error("OCR PDF processing failed: %s: %s", type(e).__name__, str(e))
        _set_cloud_degraded("Cloud OCR could not be reached. UAH will retry automatically.")
        return {
            "ok": False,
            "error_code": "CLOUD_OCR_REQUEST_FAILED",
            "status_code": 502,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "message": "Cloud OCR could not be reached. UAH will retry automatically.",
            "retryable": True,
        }


async def categorize_with_llm(md_text: str) -> dict:
    """Parse resume text with LLM. Returns dict with 'ok' key on failure."""
    headers = {
        "Authorization": f"Bearer {settings.ZAI_API_KEY}",
        "Content-Type": "application/json",
    }
    request_body = {
        "model": settings.ZAI_LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise resume data extractor. You output ONLY valid JSON with no markdown formatting, no explanation, and no extra text. Every field must match the schema exactly. Do not use reasoning or thinking - output the JSON directly."
            },
            {
                "role": "user",
                "content": CATEGORIZE_PROMPT + md_text,
            },
        ],
        "temperature": 0.1,
        "max_tokens": max(int(settings.ZAI_LLM_MAX_TOKENS), 512),
    }
    max_attempts = 3
    last_error: dict | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(settings.ZAI_LLM_URL, json=request_body, headers=headers)
        except httpx.TimeoutException as e:
            logger.error("LLM parse request timed out: %s", str(e))
            last_error = {
                "ok": False,
                "error_code": "CLOUD_LLM_TIMEOUT",
                "message": "Cloud AI timed out while parsing. UAH will retry automatically.",
                "retryable": True,
            }
            _set_cloud_degraded(last_error["message"])
        except httpx.HTTPError as e:
            logger.error("LLM parse request failed: %s: %s", type(e).__name__, str(e))
            last_error = {
                "ok": False,
                "error_code": "CLOUD_LLM_REQUEST_FAILED",
                "message": "Cloud AI could not be reached. UAH will retry automatically.",
                "retryable": True,
            }
            _set_cloud_degraded(last_error["message"])
        else:
            if resp.status_code == 200:
                result = resp.json()
                raw_content = result["choices"][0]["message"]["content"]

                if not raw_content or raw_content.strip() == "":
                    reasoning = result["choices"][0]["message"].get("reasoning_content", "")
                    if reasoning:
                        json_match = re.search(r'\{[\s\S]*\}', reasoning)
                        if json_match:
                            raw_content = json_match.group(0)
                        else:
                            return {
                                "ok": False,
                                "error_code": "LLM_EMPTY_RESPONSE",
                                "message": "AI returned no structured data. Try again or use rules-based parsing.",
                            }
                    else:
                        return {
                            "ok": False,
                            "error_code": "LLM_EMPTY_RESPONSE",
                            "message": "AI returned no structured data. Try again or use rules-based parsing.",
                        }

                cleaned = raw_content.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                try:
                    _clear_cloud_degraded()
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    logger.error("LLM returned invalid JSON: %s", cleaned[:200])
                    return {
                        "ok": False,
                        "error_code": "LLM_INVALID_JSON",
                        "message": "AI returned malformed data. Please try again.",
                    }

            classified = classify_cloud_provider_error(
                stage="llm",
                status_code=resp.status_code,
                payload=_parse_provider_payload(resp),
                response_text=resp.text,
                retry_after_seconds=_extract_retry_after_seconds(resp.headers),
            )
            logger.error("LLM API error: status=%d, body=%s", resp.status_code, resp.text[:200])
            if classified.get("retryable"):
                _set_cloud_degraded(classified.get("message"))
            last_error = {
                "ok": False,
                "error_code": classified["error_code"],
                "message": classified["message"],
                "retryable": classified.get("retryable", False),
                "retry_after_seconds": classified.get("retry_after_seconds"),
            }

        if not last_error or not last_error.get("retryable") or attempt >= max_attempts:
            break

        retry_after_seconds = last_error.get("retry_after_seconds")
        delay_seconds = retry_after_seconds if retry_after_seconds is not None else min(2 ** (attempt - 1), 8)
        await asyncio.sleep(max(float(delay_seconds), 0))

    return last_error or {
        "ok": False,
        "error_code": "CLOUD_LLM_REQUEST_FAILED",
        "message": "Cloud AI parsing failed. Please retry.",
    }


async def ocr_pdf_local(pdf_bytes: bytes) -> dict:
    """
    Local OCR replacement for ocr_pdf().
    Converts PDF to PNG via pdftoppm at LOCAL_OCR_DPI,
    sends each page image to GLM-OCR-hires on LOCAL_OCR_URL,
    returns dict with same shape as ocr_pdf() — key 'md_results' contains extracted text.

    PDF conversion uses subprocess pdftoppm (must be installed: apt install poppler-utils).
    Image encoding is base64, sent to /api/generate endpoint.
    Prompt is exactly "Text Recognition" — do not change this, it is GLM-OCR's fixed prompt.
    Clean up temp PNG files after each page.
    """
    endpoint = f"{settings.LOCAL_OCR_URL.rstrip('/')}/api/generate"

    try:
        with tempfile.TemporaryDirectory(prefix="uah-ocr-") as temp_dir:
            temp_path = Path(temp_dir)
            pdf_path = temp_path / "resume.pdf"
            pdf_path.write_bytes(pdf_bytes)
            output_prefix = temp_path / "page"

            proc = await asyncio.create_subprocess_exec(
                "pdftoppm",
                "-png",
                "-r",
                str(settings.LOCAL_OCR_DPI),
                str(pdf_path),
                str(output_prefix),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error("pdftoppm failed with return code %d: %s", proc.returncode, stderr.decode("utf-8", errors="ignore")[:200])
                return {
                    "ok": False,
                    "error_code": "OCR_PDF_CONVERSION_FAILED",
                    "status_code": 422,
                    "response_excerpt": stderr.decode("utf-8", errors="ignore")[:200],
                }

            page_paths = sorted(temp_path.glob("page-*.png"))
            if not page_paths:
                logger.error("pdftoppm produced no PNG pages")
                return {
                    "ok": False,
                    "error_code": "OCR_EMPTY_RESULTS",
                    "status_code": 422,
                    "response_excerpt": "No pages were extracted from PDF",
                }

            page_markdown: list[str] = []
            async with httpx.AsyncClient(timeout=settings.LOCAL_OCR_TIMEOUT) as client:
                for page_path in page_paths:
                    image_b64 = base64.b64encode(page_path.read_bytes()).decode("utf-8")
                    request_body = {
                        "model": settings.LOCAL_OCR_MODEL,
                        "prompt": "Text Recognition",
                        "images": [image_b64],
                        "stream": False,
                    }
                    resp = await client.post(endpoint, json=request_body)

                    # Remove each page PNG after it has been processed.
                    page_path.unlink(missing_ok=True)

                    if resp.status_code != 200:
                        logger.error("Local OCR API error: status=%d, body=%s", resp.status_code, resp.text[:200])
                        return {
                            "ok": False,
                            "error_code": "OCR_API_STATUS",
                            "status_code": resp.status_code,
                            "response_excerpt": (resp.text or "")[:200],
                        }

                    payload = resp.json()
                    page_text = (payload.get("response") or "").strip()
                    if page_text:
                        page_markdown.append(page_text)

            combined = "\n\n".join(page_markdown).strip()
            if not combined:
                return {
                    "ok": False,
                    "error_code": "OCR_EMPTY_RESULTS",
                    "status_code": 422,
                    "response_excerpt": "OCR returned no text",
                }

            return {
                "ok": True,
                "md_results": combined,
            }
    except FileNotFoundError as e:
        logger.error("pdftoppm executable not found: %s", str(e))
        return {
            "ok": False,
            "error_code": "OCR_DEPENDENCY_MISSING",
            "status_code": 500,
            "response_excerpt": "pdftoppm not found; install poppler-utils",
        }
    except httpx.TimeoutException as e:
        logger.error("Local OCR request timed out: %s", str(e))
        return {
            "ok": False,
            "error_code": "OCR_TIMEOUT",
            "status_code": 504,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
        }
    except httpx.HTTPError as e:
        logger.error("Local OCR request failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "OCR_REQUEST_EXCEPTION",
            "status_code": 502,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
        }
    except Exception as e:
        logger.error("Local OCR processing failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "OCR_REQUEST_EXCEPTION",
            "status_code": 502,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
        }


async def categorize_with_local_llm(md_text: str) -> dict:
    """
    Local LLM replacement for categorize_with_llm().
    Sends CATEGORIZE_PROMPT + md_text to qwen2.5:7b on LOCAL_LLM_URL.
    Uses /api/generate endpoint with stream=false, temperature=0.
    Returns same dict shape as categorize_with_llm() — structured JSON or error dict with 'ok': False.
    Strip markdown fences from response before JSON parse.
    """
    endpoint = f"{settings.LOCAL_LLM_URL.rstrip('/')}/api/generate"
    request_body = {
        "model": settings.LOCAL_LLM_MODEL,
        "prompt": CATEGORIZE_PROMPT + md_text,
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.LOCAL_LLM_TIMEOUT) as client:
            resp = await client.post(endpoint, json=request_body)
    except httpx.TimeoutException as e:
        logger.error("Local LLM request timed out: %s", str(e))
        return {
            "ok": False,
            "error_code": "LLM_TIMEOUT",
            "message": "AI parsing timed out. Try again or use rules-based parsing.",
        }
    except httpx.HTTPError as e:
        logger.error("Local LLM request failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "LLM_REQUEST_FAILED",
            "message": "Could not reach the AI parsing service. Please try again.",
        }

    if resp.status_code != 200:
        logger.error("Local LLM API error: status=%d, body=%s", resp.status_code, resp.text[:200])
        return {
            "ok": False,
            "error_code": "LLM_API_ERROR",
            "message": f"AI service returned status {resp.status_code}. Please retry.",
        }

    payload = resp.json()
    raw_content = (payload.get("response") or "").strip()
    if not raw_content:
        return {
            "ok": False,
            "error_code": "LLM_EMPTY_RESPONSE",
            "message": "AI returned no structured data. Try again or use rules-based parsing.",
        }

    cleaned = raw_content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Local LLM returned invalid JSON: %s", cleaned[:200])
        return {
            "ok": False,
            "error_code": "LLM_INVALID_JSON",
            "message": "AI returned malformed data. Please try again.",
        }


def _local_pipeline_probe_urls() -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for base_url in (settings.LOCAL_OCR_URL, settings.LOCAL_LLM_URL):
        cleaned = (base_url or "").strip().rstrip("/")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        urls.append(f"{cleaned}/api/tags")

    return urls


async def _probe_local_pipeline_endpoint(url: str) -> bool:
    try:
        async with httpx.AsyncClient(
            timeout=LOCAL_PIPELINE_PROBE_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)

        if 200 <= response.status_code < 300:
            return True

        logger.warning(
            "Local pipeline probe returned status %s for %s",
            response.status_code,
            url,
        )
    except httpx.TimeoutException as exc:
        logger.info("Local pipeline probe timed out for %s: %s", url, exc)
    except httpx.HTTPError as exc:
        logger.info("Local pipeline probe failed for %s: %s", url, exc)
    except Exception as exc:
        logger.warning(
            "Local pipeline probe errored for %s: %s: %s",
            url,
            type(exc).__name__,
            exc,
        )

    return False


async def get_pipeline_availability() -> dict:
    probe_urls = _local_pipeline_probe_urls()

    local_available = False
    if probe_urls:
        results = await asyncio.gather(
            *[_probe_local_pipeline_endpoint(url) for url in probe_urls],
            return_exceptions=True,
        )
        local_available = True
        for url, result in zip(probe_urls, results):
            if result is True:
                continue
            if isinstance(result, Exception):
                logger.warning(
                    "Local pipeline probe raised for %s: %s: %s",
                    url,
                    type(result).__name__,
                    result,
                )
            local_available = False

    return {
        "local": {
            "available": local_available,
            "message": None if local_available else LOCAL_PIPELINE_UNAVAILABLE_MESSAGE,
        },
        "cloud": get_cloud_provider_availability(),
        "rules": {
            "available": True,
        },
    }


async def ocr_pdf_dispatch(pdf_bytes: bytes) -> dict:
    """Route to local or cloud OCR based on USE_LOCAL_PIPELINE flag."""
    if settings.USE_LOCAL_PIPELINE:
        return await ocr_pdf_local(pdf_bytes)
    return await ocr_pdf(pdf_bytes)


async def categorize_dispatch(md_text: str) -> dict:
    """Route to local or cloud LLM based on USE_LOCAL_PIPELINE flag."""
    if settings.USE_LOCAL_PIPELINE:
        return await categorize_with_local_llm(md_text)
    return await categorize_with_llm(md_text)


def normalize_parse_method(method: str | None) -> str | None:
    """Normalize frontend/backend parse method aliases to canonical values."""
    if not method:
        return None

    normalized = method.strip().lower()
    aliases = {
        "rules": "rules",
        "local": "local",
        "local_ai": "local",
        "local_llm": "local",
        "cloud": "cloud",
        "cloud_ai": "cloud",
        "cloud_llm": "cloud",
        "zai": "cloud",
    }

    if normalized == "llm":
        return "local" if settings.USE_LOCAL_PIPELINE else "cloud"

    return aliases.get(normalized)


async def parse_markdown_by_method(md_text: str, method: str) -> dict:
    """Parse markdown using explicit source method: cloud, local, or rules."""
    normalized = normalize_parse_method(method)
    if normalized is None:
        return {
            "ok": False,
            "error_code": "PARSE_METHOD_INVALID",
            "message": f"Method must be one of: {', '.join(SUPPORTED_PARSE_METHODS)}",
        }

    if normalized == "rules":
        return parse_with_rules(md_text)
    if normalized == "local":
        return await categorize_with_local_llm(md_text)
    return await categorize_with_llm(md_text)


def _method_input_message(method: str) -> str:
    if method == "cloud":
        return "Cloud OCR could not extract text from this PDF. Please retry or switch pipelines."
    if method == "local":
        return "Local OCR could not extract text from this PDF. Please retry or switch pipelines."
    return "Rules mode requires embedded PDF text and does not use OCR. Please choose Local AI or Cloud AI for scanned resumes."


def extract_embedded_pdf_text(pdf_bytes: bytes) -> dict:
    """Extract deterministic embedded text from a PDF without OCR/model inference."""
    try:
        from pypdf import PdfReader
    except Exception as exc:
        logger.error("pypdf dependency is unavailable for rules parsing: %s", exc)
        return {
            "ok": False,
            "error_code": "RULES_TEXT_EXTRACTOR_UNAVAILABLE",
            "status_code": 500,
            "message": "Rules parser is unavailable because PDF text extraction dependency is missing.",
        }

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        fragments: list[str] = []
        for page in reader.pages:
            page_text = (page.extract_text() or "").strip()
            if page_text:
                fragments.append(page_text)

        text = "\n\n".join(fragments).strip()
        dense_length = len(re.sub(r"\s+", "", text))
        if dense_length < 40:
            return {
                "ok": False,
                "error_code": "RULES_EMBEDDED_TEXT_EMPTY",
                "status_code": 422,
                "message": "Rules parser needs embedded PDF text. This file appears scanned/image-based. Use Local AI or Cloud AI for OCR-driven parsing.",
            }

        return {
            "ok": True,
            "text": text,
            "source": "rules_embedded_pdf_text",
        }
    except Exception as exc:
        logger.error("Embedded PDF text extraction failed: %s: %s", type(exc).__name__, exc)
        return {
            "ok": False,
            "error_code": "RULES_TEXT_EXTRACTION_FAILED",
            "status_code": 422,
            "message": "Rules parser could not read embedded PDF text. Use Local AI or Cloud AI for OCR-driven parsing.",
        }


async def get_parse_input_text(pdf_bytes: bytes, method: str, resume=None) -> dict:
    """Resolve parsing input text by selected method and return normalized payload."""
    normalized = normalize_parse_method(method)
    if normalized is None:
        return {
            "ok": False,
            "error_code": "PARSE_METHOD_INVALID",
            "status_code": 400,
            "message": f"Method must be one of: {', '.join(SUPPORTED_PARSE_METHODS)}",
        }

    if resume is not None:
        cached_markdown = (getattr(resume, "raw_markdown", None) or "").strip()
        cached_method = normalize_parse_method(getattr(resume, "raw_markdown_method", None))
        cached_source = (getattr(resume, "raw_markdown_source", None) or "").strip().lower()
        if normalized == "cloud" and cached_markdown and cached_method == "cloud" and cached_source == "cloud_ocr":
            return {
                "ok": True,
                "text": cached_markdown,
                "source": "cloud_ocr",
                "cache_hit": True,
            }

    if normalized == "rules":
        return extract_embedded_pdf_text(pdf_bytes)

    ocr_result = await (ocr_pdf(pdf_bytes) if normalized == "cloud" else ocr_pdf_local(pdf_bytes))
    if not ocr_result.get("ok"):
        return {
            "ok": False,
            "error_code": ocr_result.get("error_code") or "OCR_EXTRACTION_FAILED",
            "status_code": int(ocr_result.get("status_code") or 502),
            "message": ocr_result.get("message") or _method_input_message(normalized),
            "retryable": bool(ocr_result.get("retryable", False)),
            "retry_after_seconds": ocr_result.get("retry_after_seconds"),
        }

    md_text = (ocr_result.get("md_results") or "").strip()
    if not md_text:
        return {
            "ok": False,
            "error_code": "OCR_EMPTY_RESULTS",
            "status_code": 422,
            "message": _method_input_message(normalized),
        }

    return {
        "ok": True,
        "text": md_text,
        "source": f"{normalized}_ocr",
        "cache_hit": False,
    }


def parse_with_rules(md_text: str) -> dict:
    """Parse resume text with rules engine. Returns dict with 'ok' key on failure."""
    try:
        from app.services.rule_parser import parse_resume_markdown
        result = parse_resume_markdown(md_text)
        if result is None:
            return {
                "ok": False,
                "error_code": "RULES_EMPTY_RESULT",
                "message": "Rules-based parsing produced no results. Try AI parsing instead.",
            }
        return result
    except ImportError:
        logger.error("Rule parser module not found")
        return {
            "ok": False,
            "error_code": "RULES_NOT_AVAILABLE",
            "message": "Rules-based parser is not installed.",
        }
    except Exception as e:
        logger.error("Rules parse failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "RULES_PARSE_FAILED",
            "message": "Rules-based parsing encountered an error. Try AI parsing instead.",
        }


def _normalize_string(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.lower() in PLACEHOLDER_VALUES:
        return None
    return cleaned


def _sanitize_value(value):
    if isinstance(value, str):
        return _normalize_string(value)
    if isinstance(value, list):
        sanitized = []
        for item in value:
            cleaned = _sanitize_value(item)
            if cleaned is None:
                continue
            sanitized.append(cleaned)
        return sanitized
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    return value


def _is_meaningful(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return _normalize_string(value) is not None
    if isinstance(value, list):
        return any(_is_meaningful(item) for item in value)
    if isinstance(value, dict):
        return any(_is_meaningful(item) for item in value.values())
    return bool(value)


def _resolve_field(structured, dotpath):
    parts = re.split(r'\.|(?=\[)', dotpath)
    obj = structured
    for part in parts:
        if not obj:
            return None
        idx_match = re.match(r'(\w*)\[(\d+)\]', part)
        if idx_match:
            key, idx = idx_match.group(1), int(idx_match.group(2))
            if key:
                obj = obj.get(key, [])
            if isinstance(obj, list) and len(obj) > idx:
                obj = obj[idx]
            else:
                return None
        else:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
    return obj


def check_portal_required(structured):
    missing = []
    for dotpath, label in PORTAL_REQUIRED_FIELDS.items():
        value = _resolve_field(structured, dotpath)
        if not _is_meaningful(value):
            missing.append(f"{label} ({dotpath})")
    return len(missing) == 0, missing


def validate_and_fix(structured):
    if not isinstance(structured, dict):
        structured = {}

    structured = _sanitize_value(structured) or {}
    fixes_applied = []
    info = structured.get("personal_info", {})

    email = info.get("email", "")
    if email:
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', email)
        if match:
            info["email"] = match.group(0)

    phone = info.get("phone", "")
    if phone:
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            info["phone"] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            info["phone"] = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    for edu in structured.get("education", []):
        gpa = edu.get("gpa", "")
        if gpa and isinstance(gpa, str):
            gpa_clean = re.sub(r'^[Gg][Pp][Aa]\s*:?\s*', '', gpa).strip()
            if gpa_clean != gpa:
                edu["gpa"] = gpa_clean

    for exp in structured.get("work_experience", []):
        end = exp.get("end_date", "")
        if end and isinstance(end, str) and "present" in end.lower():
            exp["is_current"] = True

    for key in ["awards", "activities", "volunteer"]:
        arr = structured.get(key, [])
        if arr:
            structured[key] = [item for item in arr if item]

    structured["personal_info"] = info

    portal_ready, missing_required = check_portal_required(structured)

    structured["_validation"] = {
        "fixes_applied": fixes_applied,
        "has_name": _is_meaningful(info.get("first_name")) and _is_meaningful(info.get("last_name")),
        "has_email": _is_meaningful(info.get("email")),
        "has_phone": _is_meaningful(info.get("phone")),
        "education_count": len(structured.get("education", [])),
        "experience_count": len(structured.get("work_experience", [])),
        "skills_count": sum(len(v) for v in structured.get("skills", {}).values() if isinstance(v, list)),
        "portal_ready": portal_ready,
        "missing_required": missing_required,
    }

    return structured
