import copy
import re
from typing import Any


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


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.lower() in PLACEHOLDER_VALUES:
        return None
    return cleaned


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _clean_string(value)
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def _split_inline_list(text: str | None) -> list[str]:
    raw = _clean_string(text)
    if not raw:
        return []
    chunks = re.split(r"[\n,;]+", raw)
    cleaned: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        item = _clean_string(chunk)
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def _compact_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {}
    compact: dict[str, Any] = {}
    for key, value in entry.items():
        if isinstance(value, list):
            cleaned = _clean_list(value)
            if cleaned:
                compact[key] = cleaned
            continue
        if isinstance(value, bool):
            compact[key] = value
            continue
        cleaned_value = _clean_string(value)
        if cleaned_value is not None:
            compact[key] = cleaned_value
    return compact


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        compact = _compact_entry(entry)
        if not compact:
            continue
        signature = repr(compact)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(compact)
    return deduped


def split_date_tokens(value: str | None) -> dict[str, str | bool | None]:
    raw = _clean_string(value)
    if not raw:
        return {"month": None, "year": None, "is_present": False}

    if raw.lower() == "present":
        return {"month": None, "year": None, "is_present": True}

    match = re.match(r"^\s*([A-Za-z]+)\s+(\d{4})\s*$", raw)
    if match:
        return {"month": match.group(1), "year": match.group(2), "is_present": False}

    year_match = re.match(r"^\s*(\d{4})\s*$", raw)
    if year_match:
        return {"month": None, "year": year_match.group(1), "is_present": False}

    return {"month": None, "year": None, "is_present": False}


def empty_canonical_profile() -> dict[str, Any]:
    return {
        "personal_info": {},
        "summary": None,
        "education": [],
        "work_experience": [],
        "skills": {
            "technical": [],
            "languages": [],
            "tools": [],
            "soft_skills": [],
        },
        "projects": [],
        "certifications": [],
        "awards": [],
        "activities": [],
        "volunteer": [],
    }


def normalize_canonical_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}

    canonical = empty_canonical_profile()

    personal_info = data.get("personal_info", {}) if isinstance(data.get("personal_info"), dict) else {}
    canonical["personal_info"] = {
        key: value
        for key, value in {
            "first_name": _clean_string(personal_info.get("first_name")),
            "middle_name": _clean_string(personal_info.get("middle_name")),
            "last_name": _clean_string(personal_info.get("last_name")),
            "full_legal_name": _clean_string(personal_info.get("full_legal_name")),
            "preferred_name": _clean_string(personal_info.get("preferred_name")),
            "suffix": _clean_string(personal_info.get("suffix")),
            "email": _clean_string(personal_info.get("email")),
            "phone": _clean_string(personal_info.get("phone")),
            "address": _clean_string(personal_info.get("address")),
            "city": _clean_string(personal_info.get("city")),
            "state": _clean_string(personal_info.get("state")),
            "zip": _clean_string(personal_info.get("zip")),
            "linkedin": _clean_string(personal_info.get("linkedin")),
            "website": _clean_string(personal_info.get("website")),
        }.items()
        if value is not None
    }

    canonical["summary"] = _clean_string(data.get("summary"))

    education: list[dict[str, Any]] = []
    for item in data.get("education", []) if isinstance(data.get("education"), list) else []:
        if not isinstance(item, dict):
            continue
        entry = {
            "institution": _clean_string(item.get("institution")),
            "degree": _clean_string(item.get("degree")),
            "field_of_study": _clean_string(item.get("field_of_study")),
            "gpa": _clean_string(item.get("gpa")),
            "start_date": _clean_string(item.get("start_date")),
            "end_date": _clean_string(item.get("end_date")),
            "honors": _clean_list(item.get("honors")),
            "relevant_coursework": _clean_list(item.get("relevant_coursework")),
        }
        compact = {key: value for key, value in entry.items() if value not in (None, [], {})}
        if compact:
            education.append(compact)
    canonical["education"] = _dedupe_entries(education)

    work_experience: list[dict[str, Any]] = []
    for item in data.get("work_experience", []) if isinstance(data.get("work_experience"), list) else []:
        if not isinstance(item, dict):
            continue
        entry = {
            "company": _clean_string(item.get("company")),
            "title": _clean_string(item.get("title")),
            "location": _clean_string(item.get("location")),
            "start_date": _clean_string(item.get("start_date")),
            "end_date": _clean_string(item.get("end_date")),
            "is_current": bool(item.get("is_current")) if item.get("is_current") is not None else None,
            "bullets": _clean_list(item.get("bullets")),
        }
        if entry.get("end_date") and entry["end_date"].lower() == "present":
            entry["is_current"] = True
        compact = {key: value for key, value in entry.items() if value not in (None, [], {})}
        if compact:
            work_experience.append(compact)
    canonical["work_experience"] = _dedupe_entries(work_experience)

    skills = data.get("skills", {}) if isinstance(data.get("skills"), dict) else {}
    canonical["skills"] = {
        "technical": _clean_list(skills.get("technical")),
        "languages": _clean_list(skills.get("languages")),
        "tools": _clean_list(skills.get("tools")),
        "soft_skills": _clean_list(skills.get("soft_skills")),
    }

    projects: list[dict[str, Any]] = []
    for item in data.get("projects", []) if isinstance(data.get("projects"), list) else []:
        if not isinstance(item, dict):
            continue
        entry = {
            "name": _clean_string(item.get("name")),
            "description": _clean_string(item.get("description")),
            "technologies": _clean_list(item.get("technologies")),
            "date": _clean_string(item.get("date")),
        }
        compact = {key: value for key, value in entry.items() if value not in (None, [], {})}
        if compact:
            projects.append(compact)
    canonical["projects"] = _dedupe_entries(projects)

    certifications: list[dict[str, Any]] = []
    for item in data.get("certifications", []) if isinstance(data.get("certifications"), list) else []:
        if isinstance(item, str):
            entry = {"name": _clean_string(item)}
        elif isinstance(item, dict):
            entry = {
                "name": _clean_string(item.get("name")),
                "issuer": _clean_string(item.get("issuer")),
                "date": _clean_string(item.get("date")),
            }
        else:
            continue
        compact = {key: value for key, value in entry.items() if value not in (None, [], {})}
        if compact:
            certifications.append(compact)
    canonical["certifications"] = _dedupe_entries(certifications)

    canonical["awards"] = _clean_list(data.get("awards"))
    canonical["activities"] = _clean_list(data.get("activities"))
    canonical["volunteer"] = _clean_list(data.get("volunteer"))

    return canonical


def _parse_education_history(text: str | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    raw = _clean_string(text)
    if not raw:
        return entries

    for line in raw.splitlines():
        cleaned = _clean_string(line)
        if not cleaned:
            continue
        parts = [part.strip() for part in cleaned.split("|")]
        entry = {
            "institution": _clean_string(parts[0]) if len(parts) > 0 else None,
            "degree": _clean_string(parts[1]) if len(parts) > 1 else None,
            "field_of_study": _clean_string(parts[2]) if len(parts) > 2 else None,
            "start_date": _clean_string(parts[3]) if len(parts) > 3 else None,
            "end_date": _clean_string(parts[4]) if len(parts) > 4 else None,
            "gpa": _clean_string(parts[5]) if len(parts) > 5 else None,
        }
        compact = {key: value for key, value in entry.items() if value is not None}
        if compact:
            entries.append(compact)
    return entries


def _parse_employment_history(text: str | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    raw = _clean_string(text)
    if not raw:
        return entries

    for line in raw.splitlines():
        cleaned = _clean_string(line)
        if not cleaned:
            continue
        parts = [part.strip() for part in cleaned.split("|")]
        entry = {
            "company": _clean_string(parts[0]) if len(parts) > 0 else None,
            "title": _clean_string(parts[1]) if len(parts) > 1 else None,
            "location": _clean_string(parts[2]) if len(parts) > 2 else None,
            "start_date": _clean_string(parts[3]) if len(parts) > 3 else None,
            "end_date": _clean_string(parts[4]) if len(parts) > 4 else None,
        }
        compact = {key: value for key, value in entry.items() if value is not None}
        if compact:
            if compact.get("end_date", "").lower() == "present":
                compact["is_current"] = True
            entries.append(compact)
    return entries


def _parse_certifications(text: str | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    raw = _clean_string(text)
    if not raw:
        return entries
    for line in raw.splitlines():
        cleaned = _clean_string(line)
        if not cleaned:
            continue
        entries.append({"name": cleaned})
    return entries


def derive_canonical_from_profile_fields(values: dict[str, Any]) -> dict[str, Any]:
    personal_info = {
        "first_name": _clean_string(values.get("first_name")),
        "middle_name": _clean_string(values.get("middle_name")),
        "last_name": _clean_string(values.get("last_name")),
        "full_legal_name": _clean_string(values.get("full_legal_name")),
        "preferred_name": _clean_string(values.get("preferred_name")),
        "suffix": _clean_string(values.get("suffix")),
        "email": _clean_string(values.get("email")),
        "phone": _clean_string(values.get("phone")),
        "address": _clean_string(values.get("street_address")),
        "city": _clean_string(values.get("city")),
        "state": _clean_string(values.get("state")),
        "zip": _clean_string(values.get("zip")),
        "linkedin": _clean_string(values.get("linkedin")),
        "website": _clean_string(values.get("portfolio")),
    }

    education: list[dict[str, Any]] = []
    primary_education = {
        "institution": _clean_string(values.get("university")),
        "degree": _clean_string(values.get("degree")),
        "field_of_study": _clean_string(values.get("major")),
        "gpa": _clean_string(values.get("gpa")),
        "end_date": _clean_string(values.get("grad_year")),
    }
    primary_education = {key: value for key, value in primary_education.items() if value is not None}
    if primary_education:
        education.append(primary_education)
    education.extend(_parse_education_history(values.get("education_history_text")))

    work_experience: list[dict[str, Any]] = []
    work_experience.extend(_parse_employment_history(values.get("employment_history_text")))
    if not work_experience and _clean_string(values.get("job_title")):
        entry = {"title": _clean_string(values.get("job_title"))}
        work_experience.append(entry)

    certifications = _parse_certifications(values.get("certifications_text"))

    canonical = {
        "personal_info": personal_info,
        "summary": _clean_string(values.get("summary")),
        "education": education,
        "work_experience": work_experience,
        "skills": {
            "technical": _split_inline_list(values.get("skills_text")),
            "languages": [],
            "tools": [],
            "soft_skills": [],
        },
        "projects": [],
        "certifications": certifications,
        "awards": [],
        "activities": [],
        "volunteer": [],
    }
    return normalize_canonical_data(canonical)


def apply_profile_updates_to_canonical(
    existing_canonical: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    canonical = normalize_canonical_data(existing_canonical)
    updates = updates or {}

    personal_map = {
        "first_name": "first_name",
        "middle_name": "middle_name",
        "last_name": "last_name",
        "full_legal_name": "full_legal_name",
        "preferred_name": "preferred_name",
        "suffix": "suffix",
        "email": "email",
        "phone": "phone",
        "street_address": "address",
        "city": "city",
        "state": "state",
        "zip": "zip",
        "linkedin": "linkedin",
        "portfolio": "website",
    }
    for field_name, canonical_key in personal_map.items():
        if field_name not in updates:
            continue
        value = _clean_string(updates.get(field_name))
        if value is None:
            canonical.setdefault("personal_info", {}).pop(canonical_key, None)
        else:
            canonical.setdefault("personal_info", {})[canonical_key] = value

    if "summary" in updates:
        canonical["summary"] = _clean_string(updates.get("summary"))

    primary_education_fields = {
        "degree": "degree",
        "major": "field_of_study",
        "university": "institution",
        "grad_year": "end_date",
        "gpa": "gpa",
    }
    if any(field in updates for field in primary_education_fields):
        education = list(canonical.get("education", []))
        primary = dict(education[0]) if education else {}
        for field_name, canonical_key in primary_education_fields.items():
            if field_name not in updates:
                continue
            value = _clean_string(updates.get(field_name))
            if value is None:
                primary.pop(canonical_key, None)
            else:
                primary[canonical_key] = value
        if primary:
            if education:
                education[0] = primary
            else:
                education = [primary]
        elif education:
            education = education[1:]
        canonical["education"] = _dedupe_entries(education)

    if "education_history_text" in updates:
        education = list(canonical.get("education", []))
        primary = education[:1]
        additional = _parse_education_history(updates.get("education_history_text"))
        canonical["education"] = _dedupe_entries(primary + additional)

    if "job_title" in updates:
        work_experience = list(canonical.get("work_experience", []))
        primary = dict(work_experience[0]) if work_experience else {}
        value = _clean_string(updates.get("job_title"))
        if value is None:
            primary.pop("title", None)
        else:
            primary["title"] = value
        if primary:
            if work_experience:
                work_experience[0] = primary
            else:
                work_experience = [primary]
        elif work_experience:
            work_experience = work_experience[1:]
        canonical["work_experience"] = _dedupe_entries(work_experience)

    if "employment_history_text" in updates:
        work_experience = list(canonical.get("work_experience", []))
        primary = work_experience[:1]
        additional = _parse_employment_history(updates.get("employment_history_text"))
        canonical["work_experience"] = _dedupe_entries(primary + additional)

    if "skills_text" in updates:
        technical = _split_inline_list(updates.get("skills_text"))
        canonical.setdefault("skills", {})
        canonical["skills"]["technical"] = technical

    if "certifications_text" in updates:
        canonical["certifications"] = _dedupe_entries(_parse_certifications(updates.get("certifications_text")))

    return normalize_canonical_data(canonical)


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = _clean_string(value)
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _derive_name_tokens(personal_info: dict[str, Any]) -> dict[str, str]:
    first = _clean_string(personal_info.get("first_name")) or ""
    middle = _clean_string(personal_info.get("middle_name")) or ""
    last = _clean_string(personal_info.get("last_name")) or ""
    suffix = _clean_string(personal_info.get("suffix")) or ""
    legal = _clean_string(personal_info.get("full_legal_name")) or ""
    preferred = _clean_string(personal_info.get("preferred_name")) or ""

    tokens: dict[str, str] = {}
    if middle:
        tokens["personal_info.middle_initial"] = middle[0].upper()

    if first or middle or last:
        full_parts = [part for part in [first, middle, last] if part]
        if full_parts:
            tokens["personal_info.first_middle_last"] = " ".join(full_parts)
            if suffix:
                tokens["personal_info.first_middle_last_with_suffix"] = f"{' '.join(full_parts)} {suffix}"

        if first and middle:
            tokens["personal_info.first_middle"] = f"{first} {middle}"
        if middle and last:
            tokens["personal_info.middle_last"] = f"{middle} {last}"
        if first and last:
            tokens["personal_info.first_last"] = f"{first} {last}"
            tokens["personal_info.last_first"] = f"{last}, {first}"
        if first and middle and last:
            tokens["personal_info.last_first_middle"] = f"{last}, {first} {middle}"

    if legal:
        tokens["personal_info.full_legal_name"] = legal
    if preferred:
        tokens["personal_info.preferred_name"] = preferred
    if suffix:
        tokens["personal_info.suffix"] = suffix
    return tokens


def _format_education_entry(entry: dict[str, Any]) -> str:
    parts = [
        entry.get("institution") or "",
        entry.get("degree") or "",
        entry.get("field_of_study") or "",
        entry.get("start_date") or "",
        entry.get("end_date") or "",
    ]
    if entry.get("gpa"):
        parts.append(entry["gpa"])
    return " | ".join(parts).strip()


def _format_work_entry(entry: dict[str, Any]) -> str:
    end_date = entry.get("end_date") or ("Present" if entry.get("is_current") else "")
    parts = [
        entry.get("company") or "",
        entry.get("title") or "",
        entry.get("location") or "",
        entry.get("start_date") or "",
        end_date or "",
    ]
    return " | ".join(parts).strip()


def derive_profile_fields_from_canonical(canonical_data: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    canonical = normalize_canonical_data(canonical_data)
    existing = existing or {}
    personal_info = canonical.get("personal_info", {})
    education = canonical.get("education", [])
    work_experience = canonical.get("work_experience", [])
    primary_education = education[0] if education else {}
    primary_experience = work_experience[0] if work_experience else {}

    skills = canonical.get("skills", {})
    all_skills = _unique_in_order(
        list(skills.get("technical", []))
        + list(skills.get("languages", []))
        + list(skills.get("tools", []))
        + list(skills.get("soft_skills", []))
    )

    return {
        "first_name": personal_info.get("first_name"),
        "middle_name": personal_info.get("middle_name"),
        "last_name": personal_info.get("last_name"),
        "full_legal_name": personal_info.get("full_legal_name"),
        "preferred_name": personal_info.get("preferred_name"),
        "suffix": personal_info.get("suffix"),
        "email": personal_info.get("email"),
        "phone": personal_info.get("phone"),
        "linkedin": personal_info.get("linkedin"),
        "portfolio": personal_info.get("website"),
        "street_address": personal_info.get("address"),
        "city": personal_info.get("city"),
        "state": personal_info.get("state"),
        "zip": personal_info.get("zip"),
        "summary": canonical.get("summary"),
        "degree": primary_education.get("degree"),
        "major": primary_education.get("field_of_study"),
        "university": primary_education.get("institution"),
        "grad_year": primary_education.get("end_date"),
        "gpa": primary_education.get("gpa"),
        "job_title": primary_experience.get("title") or existing.get("job_title"),
        "years_experience": existing.get("years_experience"),
        "skills_text": ", ".join(all_skills) if all_skills else None,
        "certifications_text": "\n".join(
            item.get("name") or ""
            for item in canonical.get("certifications", [])
            if isinstance(item, dict) and _clean_string(item.get("name"))
        ) or None,
        "professional_links_text": existing.get("professional_links_text"),
        "education_history_text": "\n".join(
            _format_education_entry(item)
            for item in education[1:]
            if isinstance(item, dict)
        ) or None,
        "employment_history_text": "\n".join(
            _format_work_entry(item)
            for item in work_experience[1:]
            if isinstance(item, dict)
        ) or None,
    }


def flatten_canonical_data(canonical_data: dict[str, Any], include_derived: bool = False) -> dict[str, Any]:
    canonical = normalize_canonical_data(canonical_data)
    tokens: dict[str, Any] = {}

    personal_info = canonical.get("personal_info", {})
    for key, value in personal_info.items():
        if value not in (None, "", [], {}):
            tokens[f"personal_info.{key}"] = value
    tokens.update(_derive_name_tokens(personal_info))

    if canonical.get("summary"):
        tokens["summary"] = canonical["summary"]

    for index, entry in enumerate(canonical.get("education", [])):
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            if value in (None, "", [], {}):
                continue
            tokens[f"education[{index}].{key}"] = value if not isinstance(value, list) else ", ".join(value)
        if include_derived:
            start = split_date_tokens(entry.get("start_date"))
            end = split_date_tokens(entry.get("end_date"))
            if start.get("month"):
                tokens[f"education[{index}].start_month"] = start["month"]
            if start.get("year"):
                tokens[f"education[{index}].start_year"] = start["year"]
            if end.get("is_present"):
                tokens[f"education[{index}].is_current"] = True
            else:
                if end.get("month"):
                    tokens[f"education[{index}].end_month"] = end["month"]
                if end.get("year"):
                    tokens[f"education[{index}].end_year"] = end["year"]

    for index, entry in enumerate(canonical.get("work_experience", [])):
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                tokens[f"work_experience[{index}].{key}"] = "\n".join(value)
            else:
                tokens[f"work_experience[{index}].{key}"] = value
        if include_derived:
            start = split_date_tokens(entry.get("start_date"))
            end = split_date_tokens(entry.get("end_date"))
            if start.get("month"):
                tokens[f"work_experience[{index}].start_month"] = start["month"]
            if start.get("year"):
                tokens[f"work_experience[{index}].start_year"] = start["year"]
            if entry.get("is_current") or end.get("is_present"):
                tokens[f"work_experience[{index}].is_current"] = True
            else:
                if end.get("month"):
                    tokens[f"work_experience[{index}].end_month"] = end["month"]
                if end.get("year"):
                    tokens[f"work_experience[{index}].end_year"] = end["year"]

    for category, items in canonical.get("skills", {}).items():
        if isinstance(items, list) and items:
            tokens[f"skills.{category}"] = ", ".join(items)

    for index, entry in enumerate(canonical.get("projects", [])):
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            if value in (None, "", [], {}):
                continue
            tokens[f"projects[{index}].{key}"] = value if not isinstance(value, list) else ", ".join(value)

    for index, entry in enumerate(canonical.get("certifications", [])):
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            if value in (None, "", [], {}):
                continue
            tokens[f"certifications[{index}].{key}"] = value

    for key in ("awards", "activities", "volunteer"):
        items = canonical.get(key, [])
        if isinstance(items, list) and items:
            tokens[key] = "\n".join(items)

    return tokens


_PATH_PART_RE = re.compile(r"([^\[\]]+)(?:\[(\d+)\])?$")


def _set_nested_value(target: dict[str, Any], path: str, value: Any) -> None:
    current: Any = target
    parts = path.split(".")
    for index, part in enumerate(parts):
        match = _PATH_PART_RE.match(part)
        if not match:
            return
        key = match.group(1)
        list_index = int(match.group(2)) if match.group(2) is not None else None
        is_last = index == len(parts) - 1

        if list_index is None:
            if is_last:
                current[key] = value
                return
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
            continue

        if key not in current or not isinstance(current[key], list):
            current[key] = []
        while len(current[key]) <= list_index:
            current[key].append({})
        if is_last:
            current[key][list_index] = value
            return
        if not isinstance(current[key][list_index], dict):
            current[key][list_index] = {}
        current = current[key][list_index]


def inflate_canonical_from_tokens(token_map: dict[str, Any]) -> dict[str, Any]:
    base = empty_canonical_profile()
    if not isinstance(token_map, dict):
        return base

    for path, value in token_map.items():
        if value in (None, "", [], {}):
            continue
        if path.endswith(".start_month") or path.endswith(".start_year") or path.endswith(".end_month") or path.endswith(".end_year"):
            continue
        if path.endswith(".is_current") and "[" in path:
            _set_nested_value(base, path, bool(value))
            continue
        if path.startswith("skills.") and isinstance(value, str):
            _set_nested_value(base, path, _split_inline_list(value))
            continue
        if path in {"awards", "activities", "volunteer"} and isinstance(value, str):
            _set_nested_value(base, path, [item for item in value.splitlines() if _clean_string(item)])
            continue
        if (path.endswith(".bullets") or path.endswith(".honors") or path.endswith(".relevant_coursework")) and isinstance(value, str):
            if path.endswith(".bullets"):
                _set_nested_value(base, path, [item for item in value.splitlines() if _clean_string(item)])
            else:
                _set_nested_value(base, path, _split_inline_list(value))
            continue
        if path.endswith(".technologies") and isinstance(value, str):
            _set_nested_value(base, path, _split_inline_list(value))
            continue
        _set_nested_value(base, path, value)

    return normalize_canonical_data(base)


def profile_to_values(profile: Any) -> dict[str, Any]:
    return {
        "name": getattr(profile, "name", None),
        "first_name": getattr(profile, "first_name", None),
        "middle_name": getattr(profile, "middle_name", None),
        "last_name": getattr(profile, "last_name", None),
        "full_legal_name": getattr(profile, "full_legal_name", None),
        "preferred_name": getattr(profile, "preferred_name", None),
        "suffix": getattr(profile, "suffix", None),
        "email": getattr(profile, "email", None),
        "phone": getattr(profile, "phone", None),
        "linkedin": getattr(profile, "linkedin", None),
        "portfolio": getattr(profile, "portfolio", None),
        "street_address": getattr(profile, "street_address", None),
        "city": getattr(profile, "city", None),
        "state": getattr(profile, "state", None),
        "zip": getattr(profile, "zip", None),
        "summary": getattr(profile, "summary", None),
        "work_auth": getattr(profile, "work_auth", None),
        "requires_sponsorship": getattr(profile, "requires_sponsorship", None),
        "degree": getattr(profile, "degree", None),
        "major": getattr(profile, "major", None),
        "university": getattr(profile, "university", None),
        "grad_year": getattr(profile, "grad_year", None),
        "gpa": getattr(profile, "gpa", None),
        "years_experience": getattr(profile, "years_experience", None),
        "job_title": getattr(profile, "job_title", None),
        "skills_text": getattr(profile, "skills_text", None),
        "certifications_text": getattr(profile, "certifications_text", None),
        "professional_links_text": getattr(profile, "professional_links_text", None),
        "education_history_text": getattr(profile, "education_history_text", None),
        "employment_history_text": getattr(profile, "employment_history_text", None),
        "demographic_gender": getattr(profile, "demographic_gender", None),
        "demographic_ethnicity": getattr(profile, "demographic_ethnicity", None),
        "veteran_status": getattr(profile, "veteran_status", None),
        "disability_status": getattr(profile, "disability_status", None),
        "california_resident": getattr(profile, "california_resident", None),
        "canonical_data": copy.deepcopy(getattr(profile, "canonical_data", None)),
        "token_map": copy.deepcopy(getattr(profile, "token_map", None)),
    }


def sync_profile_storage(profile: Any) -> dict[str, Any]:
    values = profile_to_values(profile)
    if isinstance(values.get("canonical_data"), dict) and values["canonical_data"]:
        canonical = normalize_canonical_data(values["canonical_data"])
    else:
        canonical = derive_canonical_from_profile_fields(values)

    flat_updates = derive_profile_fields_from_canonical(canonical, existing=values)
    for key, value in flat_updates.items():
        setattr(profile, key, value)

    profile.canonical_data = canonical
    profile.token_map = flatten_canonical_data(canonical, include_derived=True)
    return canonical


def build_profile_from_review(profile: Any, reviewed_data: dict[str, Any]) -> dict[str, Any]:
    canonical = normalize_canonical_data(reviewed_data)
    profile.canonical_data = canonical
    return sync_profile_storage(profile)


def _append_unique_entries(target: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined = [_compact_entry(entry) for entry in target]
    filtered = [entry for entry in combined if entry]
    seen = {repr(entry) for entry in filtered}
    for entry in incoming:
        compact = _compact_entry(entry)
        if not compact:
            continue
        signature = repr(compact)
        if signature in seen:
            continue
        seen.add(signature)
        filtered.append(compact)
    return filtered


def friendly_path_label(path: str) -> str:
    label = path
    label = re.sub(r"personal_info\.", "", label)
    label = label.replace("work_experience", "Work Experience")
    label = label.replace("education", "Education")
    label = label.replace("certifications", "Certifications")
    label = label.replace("projects", "Projects")
    label = label.replace("skills.", "Skills ")
    label = label.replace("_", " ")
    label = re.sub(r"\[(\d+)\]", lambda match: f" #{int(match.group(1)) + 1}", label)
    return " ".join(part.capitalize() for part in label.split())


def generate_review_conflicts(existing_canonical: dict[str, Any], incoming_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    existing_tokens = flatten_canonical_data(existing_canonical, include_derived=False)
    incoming_tokens = flatten_canonical_data(incoming_canonical, include_derived=False)
    conflicts: list[dict[str, Any]] = []
    for path, incoming_value in incoming_tokens.items():
        existing_value = existing_tokens.get(path)
        if existing_value in (None, "", [], {}) or incoming_value in (None, "", [], {}):
            continue
        if existing_value == incoming_value:
            continue
        conflicts.append(
            {
                "id": path,
                "path": path,
                "label": friendly_path_label(path),
                "existing_value": existing_value,
                "incoming_value": incoming_value,
                "resolution": "existing",
            }
        )
    conflicts.sort(key=lambda item: item["label"])
    return conflicts


def merge_review_into_profile(
    existing_canonical: dict[str, Any],
    incoming_canonical: dict[str, Any],
    conflict_resolutions: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conflict_resolutions = conflict_resolutions or {}
    existing_tokens = flatten_canonical_data(existing_canonical, include_derived=False)
    incoming_tokens = flatten_canonical_data(incoming_canonical, include_derived=False)
    conflicts = generate_review_conflicts(existing_canonical, incoming_canonical)

    merged_tokens = dict(existing_tokens)
    conflict_paths = {item["path"] for item in conflicts}

    for path, value in incoming_tokens.items():
        if value in (None, "", [], {}):
            continue
        if path not in merged_tokens or merged_tokens[path] in (None, "", [], {}):
            merged_tokens[path] = value
            continue
        if path in conflict_paths:
            if conflict_resolutions.get(path) == "incoming":
                merged_tokens[path] = value
            continue
        merged_tokens[path] = value

    merged = inflate_canonical_from_tokens(merged_tokens)

    # Preserve richer array sections by appending unique incoming items after token merge.
    for section in ("education", "work_experience", "projects", "certifications"):
        merged[section] = _append_unique_entries(
            merged.get(section, []) if isinstance(merged.get(section), list) else [],
            incoming_canonical.get(section, []) if isinstance(incoming_canonical.get(section), list) else [],
        )

    for section in ("awards", "activities", "volunteer"):
        merged[section] = _unique_in_order(
            list(existing_canonical.get(section, []) if isinstance(existing_canonical.get(section), list) else [])
            + list(incoming_canonical.get(section, []) if isinstance(incoming_canonical.get(section), list) else [])
        )

    for category in ("technical", "languages", "tools", "soft_skills"):
        existing_items = existing_canonical.get("skills", {}).get(category, [])
        incoming_items = incoming_canonical.get("skills", {}).get(category, [])
        merged.setdefault("skills", {})
        merged["skills"][category] = _unique_in_order(
            list(existing_items if isinstance(existing_items, list) else [])
            + list(incoming_items if isinstance(incoming_items, list) else [])
        )

    return normalize_canonical_data(merged), conflicts
