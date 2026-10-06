"""Safe inventory availability helper.

Compares service/country availability snapshots. It intentionally contains
no phone numbers, SMS bodies, authentication codes, or allocation logic.
"""
import re

def build_availability_snapshot(services, country_lookup):
    snapshot = {}
    for service, ranges in (services or {}).items():
        name = str(service).strip()
        if not name:
            continue
        for raw in ranges or []:
            digits = re.sub(r"[^0-9]", "", str(raw))
            prefix = country_lookup(digits)
            if not prefix:
                continue
            snapshot[(name.lower(), prefix)] = name
    return snapshot

def new_availability(previous, current):
    previous_keys = set(previous or {})
    return {key: current[key] for key in set(current or {}) - previous_keys}
