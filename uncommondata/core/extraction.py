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
        subprocess.run(["pdftotext", "-layout", filename, output_filename], check=True)
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


def _clean_number(value: str) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    if not value or value.lower() in {"n/a", "na", "null", "none", "--", "-"}:
        return None
    value = re.sub(r"[$,%\s]", "", value)
    value = value.replace(",", "")
    if not value:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def _normalize(text: str) -> str:
    return text.replace("\r", "")


def _find_value_near_label(text: str, label_patterns) -> Optional[int]:
    if isinstance(label_patterns, str):
        label_patterns = [label_patterns]
    lines = _normalize(text).split("\n")
    for pattern in label_patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        for idx, line in enumerate(lines):
            if regex.search(line):
                window = " ".join(lines[idx: idx + 3])
                nums = re.findall(r"\$?\d[\d,]*", window)
                if nums:
                    return _clean_number(nums[-1])
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
        "men_applied": [r"men\s+who\s+applied", r"male\s+applied"],
        "women_applied": [r"women\s+who\s+applied", r"female\s+applied"],
        "another_gender_applied": [r"another\s+gender\s+who\s+applied", r"non[- ]binary.*applied"],
        "unknown_gender_applied": [r"unknown\s+gender\s+who\s+applied", r"unknown.*applied"],
        "men_admitted": [r"men\s+who\s+were\s+admitted", r"male\s+admitted"],
        "women_admitted": [r"women\s+who\s+were\s+admitted", r"female\s+admitted"],
        "another_gender_admitted": [r"another\s+gender\s+who\s+were\s+admitted", r"non[- ]binary.*admitted"],
        "unknown_gender_admitted": [r"unknown\s+gender\s+who\s+were\s+admitted", r"unknown.*admitted"],
    }
    for key, patterns in label_map.items():
        result[key] = _find_value_near_label(text, patterns)

    # Common Data Set table row fallback: look for C1 and then a row with 8 values.
    c1_match = re.search(r"C1.*?(?:\n.*?){0,8}", _normalize(text), re.IGNORECASE | re.DOTALL)
    if c1_match and any(v is None for v in result.values()):
        nearby = c1_match.group(0)
        nums = [_clean_number(n) for n in re.findall(r"\d[\d,]*", nearby)]
        if len(nums) >= 8:
            keys = list(result.keys())
            for i, key in enumerate(keys):
                if result[key] is None:
                    result[key] = nums[i]
    return result


def extract_fields_from_file(filename: str) -> Dict[str, Optional[int]]:
    text = _read_text_for_extraction(filename)
    text = _normalize(text)
    data = dict(EXPECTED_FIELDS)

    data.update(_extract_c1_table(text))

    label_patterns = {
        "tuition_undergraduates": [r"tuition\s*\(\s*undergraduates\s*\)", r"g1.*tuition"],
        "required_fees_undergraduates": [r"required\s+fees.*undergraduates"],
        "food_and_housing_on_campus_undergraduates": [r"food\s+and\s+housing\s*\(\s*on-?campus\s*\).*undergraduates"],
        "housing_only_on_campus_undergraduates": [r"housing\s+only\s*\(\s*on-?campus\s*\).*undergraduates"],
        "food_only_on_campus_meal_plan_undergraduates": [r"food\s+only\s*\(\s*on-?campus\s+meal\s+plan\s*\).*undergraduates", r"food\s+only.*meal\s+plan"],
        "degree_seeking_undergraduate_students": [r"number\s+of\s+degree-?seeking\s+undergraduate\s+students", r"^\s*a\.?\s+number\s+of\s+degree-?seeking\s+undergraduate\s+students"],
        "applied_for_need_based_financial_aid": [r"applied\s+for\s+need-?\s*based\s+financial\s+aid"],
        "determined_to_have_financial_need": [r"determined\s+to\s+have\s+financial\s+need"],
        "awarded_any_financial_aid": [r"awarded\s+any\s+financial\s+aid"],
        "average_financial_aid_package": [r"average\s+financial\s+aid\s+package"],
    }
    for key, patterns in label_patterns.items():
        data[key] = _find_value_near_label(text, patterns)

    return data
