import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional


EXPECTED_FIELDS = {
    "tuition_undergraduates": None,
    "required_fees_undergraduates": None,
    "food_and_housing_on_campus_undergraduates": None,
    "housing_only_on_campus_undergraduates": None,
    "food_only_on_campus_meal_plan_undergraduates": None,
    "degree_seeking_undergraduate_students": None,
    "applied_for_need_based_financial_aid": None,
    "determined_to_have_financial_need": None,
    "awarded_any_financial_aid": None,
    "average_financial_aid_package": None,
    "men_applied": None,
    "women_applied": None,
    "another_gender_applied": None,
    "unknown_gender_applied": None,
    "men_admitted": None,
    "women_admitted": None,
    "another_gender_admitted": None,
    "unknown_gender_admitted": None,
}


def pdf_to_text(filename: str) -> str:
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Input file not found: {filename}")

    output_filename = filename + ".txt"
    try:
        subprocess.run(
            ["pdftotext", "-layout", filename, output_filename],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftotext failed with exit code {e.returncode}") from e

    return output_filename


def _read_text_for_extraction(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            txt_path = pdf_to_text(filename)
            return Path(txt_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    return Path(filename).read_text(encoding="utf-8", errors="ignore")


def _normalize(text: str) -> str:
    return text.replace("\r", "")


def _clean_number(value: str) -> Optional[int]:
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    lowered = value.lower()
    if lowered in {"n/a", "na", "null", "none", "--", "-"}:
        return None

    value = value.replace("$", "").replace(",", "").replace("%", "").strip()
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def _extract_number_from_line(line: str) -> Optional[int]:
    """
    Extract the most likely value from a single line.
    Prefer the LAST token on that line, since these CDS rows usually end
    with the target value.
    """
    line = line.strip()
    if not line:
        return None

    if re.search(r"(?:--|\bN/?A\b|\bNone\b)$", line, re.IGNORECASE):
        return None

    matches = re.findall(r"\$?\d[\d,]*", line)
    if not matches:
        return None

    return _clean_number(matches[-1])


def _find_value_on_matching_line(text: str, label_patterns) -> Optional[int]:
    """
    Find a line matching one of the label patterns and extract the value
    from THAT line only.
    """
    if isinstance(label_patterns, str):
        label_patterns = [label_patterns]

    lines = _normalize(text).split("\n")

    for pattern in label_patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        for line in lines:
            if regex.search(line):
                value = _extract_number_from_line(line)
                if value is not None:
                    return value
                if re.search(r"--|\bN/?A\b|\bNone\b", line, re.IGNORECASE):
                    return None
    return None


def _find_value_on_line_or_next_lines(text: str, label_patterns, lookahead: int = 2) -> Optional[int]:
    """
    For cases where PDF text rendering may put the label on one line and the
    value on the next line(s). First try the matched line itself, then a small
    lookahead.
    """
    if isinstance(label_patterns, str):
        label_patterns = [label_patterns]

    lines = _normalize(text).split("\n")

    for pattern in label_patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        for i, line in enumerate(lines):
            if regex.search(line):
                value = _extract_number_from_line(line)
                if value is not None:
                    return value
                if re.search(r"--|\bN/?A\b|\bNone\b", line, re.IGNORECASE):
                    return None

                for j in range(1, lookahead + 1):
                    if i + j < len(lines):
                        nxt = lines[i + j].strip()
                        value = _extract_number_from_line(nxt)
                        if value is not None:
                            return value
                        if re.fullmatch(r"--|N/?A|None|-", nxt, re.IGNORECASE):
                            return None
    return None


def _extract_c1_table(text: str) -> Dict[str, Optional[int]]:
    result = {
        "men_applied": None,
        "women_applied": None,
        "another_gender_applied": None,
        "unknown_gender_applied": None,
        "men_admitted": None,
        "women_admitted": None,
        "another_gender_admitted": None,
        "unknown_gender_admitted": None,
    }

    label_map = {
        "men_applied": [
            r"total\s+first-time,\s*first-year\s+men\s+who\s+applied",
            r"\bmen\s+who\s+applied\b",
            r"\bmale\s+applied\b",
        ],
        "women_applied": [
            r"total\s+first-time,\s*first-year\s+women\s+who\s+applied",
            r"\bwomen\s+who\s+applied\b",
            r"\bfemale\s+applied\b",
        ],
        "another_gender_applied": [
            r"total\s+first-time,\s*first-year\s+another\s+gender\s+who\s+applied",
            r"\banother\s+gender\s+who\s+applied\b",
            r"\bnon[- ]binary.*applied\b",
        ],
        "unknown_gender_applied": [
            r"total\s+first-time,\s*first-year\s+unknown\s+gender\s+who\s+applied",
            r"\bunknown\s+gender\s+who\s+applied\b",
            r"\bunknown.*applied\b",
        ],
        "men_admitted": [
            r"total\s+first-time,\s*first-year\s+men\s+who\s+were\s+admitted",
            r"\bmen\s+who\s+were\s+admitted\b",
            r"\bmale\s+admitted\b",
        ],
        "women_admitted": [
            r"total\s+first-time,\s*first-year\s+women\s+who\s+were\s+admitted",
            r"\bwomen\s+who\s+were\s+admitted\b",
            r"\bfemale\s+admitted\b",
        ],
        "another_gender_admitted": [
            r"total\s+first-time,\s*first-year\s+another\s+gender\s+who\s+were\s+admitted",
            r"\banother\s+gender\s+who\s+were\s+admitted\b",
            r"\bnon[- ]binary.*admitted\b",
        ],
        "unknown_gender_admitted": [
            r"total\s+first-time,\s*first-year\s+unknown\s+gender\s+who\s+were\s+admitted",
            r"\bunknown\s+gender\s+who\s+were\s+admitted\b",
            r"\bunknown.*admitted\b",
        ],
    }

    for key, patterns in label_map.items():
        result[key] = _find_value_on_line_or_next_lines(text, patterns, lookahead=2)

    return result


def extract_fields_from_file(filename: str) -> Dict[str, Optional[int]]:
    text = _read_text_for_extraction(filename)
    text = _normalize(text)
    data = dict(EXPECTED_FIELDS)

    data.update(_extract_c1_table(text))

    label_patterns = {
        "tuition_undergraduates": [
            r"tuition\s*\(\s*undergraduates\s*\)",
            r"\bg1\b.*tuition",
        ],
        "required_fees_undergraduates": [
            r"required\s+fees:?\s*\(\s*undergraduates\s*\)",
            r"required\s+fees.*undergraduates",
        ],
        "food_and_housing_on_campus_undergraduates": [
            r"food\s+and\s+housing\s*\(\s*on-?campus\s*\):?\s*\(\s*undergraduates\s*\)",
            r"food\s+and\s+housing.*undergraduates",
        ],
        "housing_only_on_campus_undergraduates": [
            r"housing\s+only\s*\(\s*on-?campus\s*\):?\s*\(\s*undergraduates\s*\)",
            r"housing\s+only.*undergraduates",
        ],
        "food_only_on_campus_meal_plan_undergraduates": [
            r"food\s+only\s*\(\s*on-?campus\s+meal\s+plan\s*\):?\s*\(\s*undergraduates\s*\)",
            r"food\s+only.*meal\s+plan.*undergraduates",
        ],
        "degree_seeking_undergraduate_students": [
            r"^a\.?\s+number\s+of\s+degree-?seeking\s+undergraduate\s+students",
            r"number\s+of\s+degree-?seeking\s+undergraduate\s+students",
        ],
        "applied_for_need_based_financial_aid": [
            r"^b\.?\s+number\s+of\s+students\s+in\s+line\s+a\s+who\s+applied\s+for\s+need-?\s*based\s+financial\s+aid",
            r"applied\s+for\s+need-?\s*based\s+financial\s+aid",
        ],
        "determined_to_have_financial_need": [
            r"^c\.?\s+number\s+of\s+students\s+in\s+line\s+b\s+who\s+were\s+determined\s+to\s+have\s+financial\s+need",
            r"determined\s+to\s+have\s+financial\s+need",
        ],
        "awarded_any_financial_aid": [
            r"^d\.?\s+number\s+of\s+students\s+in\s+line\s+c\s+who\s+were\s+awarded\s+any\s+financial\s+aid",
            r"awarded\s+any\s+financial\s+aid",
        ],
        "average_financial_aid_package": [
            r"^j\.?\s+the\s+average\s+financial\s+aid\s+package\s+of\s+those\s+in\s+line\s+d",
            r"average\s+financial\s+aid\s+package",
        ],
    }

    for key, patterns in label_patterns.items():
        data[key] = _find_value_on_line_or_next_lines(text, patterns, lookahead=2)

    return data
