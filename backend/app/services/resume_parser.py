import re
import json
import base64
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

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
            logger.error(
                f"OCR API error: status={resp.status_code}, url={settings.ZAI_OCR_URL}, "
                f"response_text={resp.text[:200]}"
            )
            return {
                "ok": False,
                "error_code": "OCR_API_STATUS",
                "status_code": resp.status_code,
                "response_excerpt": (resp.text or "")[:200],
            }

        payload = resp.json()
        payload["ok"] = True
        return payload
    except httpx.TimeoutException as e:
        logger.error("OCR request timed out: %s", str(e))
        return {
            "ok": False,
            "error_code": "OCR_TIMEOUT",
            "status_code": 504,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
        }
    except httpx.HTTPError as e:
        logger.error("OCR request failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "OCR_REQUEST_EXCEPTION",
            "status_code": 502,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
        }
    except Exception as e:
        logger.error("OCR PDF processing failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "OCR_REQUEST_EXCEPTION",
            "status_code": 502,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
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
        "max_tokens": 8192,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(settings.ZAI_LLM_URL, json=request_body, headers=headers)
    except httpx.TimeoutException as e:
        logger.error("LLM parse request timed out: %s", str(e))
        return {
            "ok": False,
            "error_code": "LLM_TIMEOUT",
            "message": "AI parsing timed out. Try again or use rules-based parsing.",
        }
    except httpx.HTTPError as e:
        logger.error("LLM parse request failed: %s: %s", type(e).__name__, str(e))
        return {
            "ok": False,
            "error_code": "LLM_REQUEST_FAILED",
            "message": "Could not reach the AI parsing service. Please try again.",
        }

    if resp.status_code != 200:
        logger.error("LLM API error: status=%d, body=%s", resp.status_code, resp.text[:200])
        return {
            "ok": False,
            "error_code": "LLM_API_ERROR",
            "message": f"AI service returned status {resp.status_code}. Please retry.",
        }

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
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON: %s", cleaned[:200])
        return {
            "ok": False,
            "error_code": "LLM_INVALID_JSON",
            "message": "AI returned malformed data. Please try again.",
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
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(f"{label} ({dotpath})")
    return len(missing) == 0, missing


def validate_and_fix(structured):
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
        "has_name": bool(info.get("first_name")),
        "has_email": bool(info.get("email")),
        "has_phone": bool(info.get("phone")),
        "education_count": len(structured.get("education", [])),
        "experience_count": len(structured.get("work_experience", [])),
        "skills_count": sum(len(v) for v in structured.get("skills", {}).values() if isinstance(v, list)),
        "portal_ready": portal_ready,
        "missing_required": missing_required,
    }

    return structured
