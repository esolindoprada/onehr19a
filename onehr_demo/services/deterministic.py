
import hashlib
import random
import re
from datetime import datetime, time, timedelta
import pytz
from odoo import fields
from odoo.exceptions import ValidationError

def _key_part(value):
    value = (value or "").strip().lower().replace(" ", "_")
    value = re.sub(r"[^a-z0-9_.-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_.-")
    if not value:
        raise ValidationError("Deterministic demo key parts cannot be empty.")
    return value

def stable_demo_key(scenario_code, domain, entity, stable_key):
    parts = [_key_part(scenario_code), _key_part(domain), _key_part(entity), _key_part(stable_key)]
    value = ".".join(parts)
    if len(value) <= 240:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{'.'.join(parts[:3])}.{digest}"

def stable_identifier(prefix, stable_key, max_length=64):
    prefix = re.sub(r"[^A-Za-z0-9]+", "-", (prefix or "DEMO").upper()).strip("-")
    raw = f"{prefix}-{stable_key.upper().replace('.', '-')}"
    if len(raw) <= max_length:
        return raw
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
    head = raw[:max(1, max_length - 17)].rstrip("-")
    return f"{head}-{digest}"

def deterministic_rng(seed, namespace):
    material = f"{int(seed)}:{_key_part(namespace)}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))

def scenario_date(scenario, days=0):
    base = fields.Date.to_date(scenario.reference_date)
    if not base:
        raise ValidationError("Scenario reference date is required.")
    return base + timedelta(days=days)

def scenario_datetime(scenario, days=0, hours=0, minutes=0):
    base = fields.Datetime.to_datetime(scenario.reference_datetime)
    if not base:
        raise ValidationError("Scenario reference datetime is required.")
    return base + timedelta(days=days, hours=hours, minutes=minutes)

def local_clock_to_utc_naive(reference_date, hour, minute, timezone_name):
    if timezone_name not in pytz.all_timezones_set:
        raise ValidationError(f"Unsupported demo timezone: {timezone_name}")
    day = fields.Date.to_date(reference_date)
    zone = pytz.timezone(timezone_name)
    local = zone.localize(datetime.combine(day, time(hour=hour, minute=minute)), is_dst=None)
    return local.astimezone(pytz.UTC).replace(tzinfo=None)

