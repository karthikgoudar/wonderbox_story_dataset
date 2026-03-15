#!/usr/bin/env python3
"""
Validate processed JSON story files.

Checks:
- required top-level fields exist
- exactly 5 scenes exist and scene types are correct and in expected order
- the `age_group` reported in the JSON matches the processed folder
"""
import json
import sys
from pathlib import Path
from typing import List

REQUIRED_FIELDS = [
    "id",
    "title",
    "age_group",
    "reading_level",
    "theme",
    "characters",
    "word_count",
    "moral",
    "scenes",
    "story",
]

EXPECTED_SCENE_TYPES = ["introduction", "conflict", "journey", "turning_point", "resolution"]


def validate_file(path: Path) -> List[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"invalid_json: {e}"]

    for f in REQUIRED_FIELDS:
        if f not in data:
            errors.append(f"missing_field: {f}")

    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != 5:
        errors.append(f"scenes_count: expected 5, found {len(scenes)}")
    else:
        for i, s in enumerate(scenes):
            expected_type = EXPECTED_SCENE_TYPES[i]
            stype = s.get("type")
            if stype != expected_type:
                errors.append(f"scene_type_mismatch: index {i} expected {expected_type}, found {stype}")
            # check required keys inside each scene
            for key in ("summary", "text", "image_prompt"):
                if key not in s:
                    errors.append(f"scene_missing_{key}: scene {i}")

    # Verify age_group matches folder
    parent = path.parent.name
    folder_map = {"age_3_5": "3-5", "age_6_8": "6-8", "age_9_12": "9-12"}
    expected_age = folder_map.get(parent)
    if expected_age and data.get("age_group") != expected_age:
        errors.append(f"age_group_mismatch: folder {parent} implies {expected_age}, json has {data.get('age_group')}")

    return errors


def main():
    processed = Path("processed")
    if not processed.exists():
        print("No processed/ directory found. Nothing to validate.")
        return

    json_files = list(processed.rglob("*.json"))
    total = len(json_files)
    print(f"Validating {total} JSON files...")
    problems = 0

    for jf in json_files:
        errs = validate_file(jf)
        if errs:
            problems += 1
            print(f"ERROR in {jf}:")
            for e in errs:
                print(f"  - {e}")

    if problems:
        print(f"Validation finished: {problems} files with problems.")
        sys.exit(1)
    else:
        print("All files passed validation.")


if __name__ == "__main__":
    main()
