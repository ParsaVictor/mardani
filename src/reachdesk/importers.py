"""CSV importers: LinkedIn's official Connections.csv export and any generic CSV."""
from __future__ import annotations

import csv
import io

ALIASES = {
    "full_name": ["full name", "name", "contact", "person"],
    "first_name": ["first name", "firstname", "given name"],
    "last_name": ["last name", "lastname", "surname", "family name"],
    "title": ["title", "position", "job title", "headline", "role"],
    "company": ["company", "organization", "organisation", "employer", "account"],
    "location": ["location", "city", "region", "country"],
    "url": ["url", "linkedin", "linkedin url", "profile", "profile url", "link"],
    "email": ["email", "email address", "e-mail"],
    "body": ["body", "text", "notes", "about", "description", "post"],
    "consent_basis": ["consent basis", "consent_basis", "consent"],
    "kind": ["kind", "type"],
}
_LOOKUP = {alias: field for field, names in ALIASES.items() for alias in names}


def _decode(data: bytes | str) -> str:
    if isinstance(data, str):
        return data.lstrip("﻿")
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    return data.decode("utf-8", "replace")


def _find_header(lines: list[str]) -> int:
    """LinkedIn puts a free-text 'Notes' preamble above the real header row."""
    for index, line in enumerate(lines[:15]):
        cells = next(csv.reader([line]), [])
        known = sum(1 for c in cells if c.strip().lower() in _LOOKUP)
        if known >= 2:
            return index
    return 0


def is_linkedin_connections(text: str) -> bool:
    lines = _decode(text).splitlines()
    head = lines[_find_header(lines)].lower() if lines else ""
    return "first name" in head and "connected on" in head


def parse_csv(data: bytes | str) -> list[dict]:
    text = _decode(data)
    lines = text.splitlines()
    if not lines:
        return []
    start = _find_header(lines)
    connections = is_linkedin_connections(text)
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    records = []
    for raw in reader:
        record: dict[str, str] = {}
        for key, value in raw.items():
            field = _LOOKUP.get((key or "").strip().lower())
            if field and value and value.strip() and field not in record:
                record[field] = value.strip()
        first, last = record.pop("first_name", ""), record.pop("last_name", "")
        if not record.get("full_name") and (first or last):
            record["full_name"] = f"{first} {last}".strip()
        if not any(record.get(k) for k in ("full_name", "url", "email", "body")):
            continue
        record.setdefault("kind", "person")
        if record["kind"] not in ("person", "post", "job"):
            record["kind"] = "person"
        if connections:
            record["connection_state"] = "connected"
            record["consent_basis"] = "existing_connection"
            record["source"] = "linkedin_export"
        else:
            record.setdefault("source", "csv")
        records.append(record)
    return records


def export_csv(rows: list[dict], columns: list[str]) -> str:
    """Write CSV with spreadsheet formula injection neutralised."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(columns)
    for row in rows:
        cells = []
        for column in columns:
            value = str(row.get(column, "") if row.get(column) is not None else "")
            if value[:1] in ("=", "+", "-", "@", "\t", "\r"):
                value = "'" + value
            cells.append(value)
        writer.writerow(cells)
    return out.getvalue()
