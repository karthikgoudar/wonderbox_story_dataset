#!/usr/bin/env python3
"""
Read raw stories and call an LLM to extract structured metadata, saving JSON files
into the appropriate `processed/age_*` folder.

This starter includes a `call_llm` placeholder that tries to use OpenAI if configured,
and a local fallback that returns a conservative mock result so junior contributors
can run the pipeline without API keys.
"""
import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

PROMPT_FILE = Path("prompts/metadata_prompt.txt")
IMAGE_PROMPT_TEMPLATE = Path("prompts/image_prompt_template.txt")


def call_llm(prompt: str, max_tokens: int = 800) -> str:
    """
    Placeholder LLM call. If OpenAI is configured via `OPENAI_API_KEY`, the function will
    attempt to call it. Otherwise, this returns a mocked JSON response for testing.
    Contributors should replace or extend this function with their preferred client.
    """
    try:
        import openai
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            openai.api_key = key
            resp = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return resp.choices[0].text.strip()
    except Exception:
        # fall through to mock
        pass

    # Mocked minimal response used for offline testing
    mock = {
        "title": "Untitled Story",
        "age_group": "6-8",
        "reading_level": "elementary",
        "theme": "friendship",
        "characters": ["Child A", "Friend B"],
        "word_count": 0,
        "moral": "Be kind to others.",
        "scenes": [
            {"type": "introduction", "summary": "Intro", "text": "", "image_prompt": ""},
            {"type": "conflict", "summary": "Conflict", "text": "", "image_prompt": ""},
            {"type": "journey", "summary": "Journey", "text": "", "image_prompt": ""},
            {"type": "turning_point", "summary": "Turning point", "text": "", "image_prompt": ""},
            {"type": "resolution", "summary": "Resolution", "text": "", "image_prompt": ""}
        ],
        "story": ""
    }
    return json.dumps(mock)


def generate_id(counter: int) -> str:
    return f"WBX_{counter:06d}"


def simple_clean(text: str) -> str:
    # basic cleaning: collapse multiple spaces and trim
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def extract_and_save(raw_path: Path, processed_base: Path, counter: int) -> int:
    raw_text = raw_path.read_text(encoding="utf-8")
    # strip source comments if present
    raw_text = re.sub(r"^#.*$", "", raw_text, flags=re.MULTILINE).strip()
    story = simple_clean(raw_text)

    with open(PROMPT_FILE, "r", encoding="utf-8") as pf:
        prompt_template = pf.read()

    # Build a prompt by appending the story
    prompt = prompt_template + "\n\nSTORY:\n" + story

    print(f"Calling LLM for: {raw_path}")
    response_text = call_llm(prompt)

    try:
        data: Dict[str, Any] = json.loads(response_text)
    except Exception:
        # If the LLM returns a raw JSON-like string with trailing text, try to extract JSON
        m = re.search(r"(\{.*\})", response_text, flags=re.DOTALL)
        if not m:
            raise RuntimeError("LLM did not return valid JSON")
        data = json.loads(m.group(1))

    # Ensure counts and story are set
    data.setdefault("story", story)
    data["word_count"] = len(data.get("story", "").split())

    # Ensure scenes exist and have required keys
    scenes = data.get("scenes", [])
    if len(scenes) != 5:
        # Fill missing scenes with placeholders
        default_types = ["introduction", "conflict", "journey", "turning_point", "resolution"]
        new_scenes = []
        for i, t in enumerate(default_types):
            if i < len(scenes):
                s = scenes[i]
                s.setdefault("type", t)
                s.setdefault("summary", "")
                s.setdefault("text", "")
                s.setdefault("image_prompt", "")
                new_scenes.append(s)
            else:
                new_scenes.append({"type": t, "summary": "", "text": "", "image_prompt": ""})
        data["scenes"] = new_scenes

    # Assign an ID and compute filename
    story_id = generate_id(counter)
    data["id"] = story_id

    age_mapping = {"3-5": "age_3_5", "6-8": "age_6_8", "9-12": "age_9_12"}
    age_group = data.get("age_group", "6-8")
    dest_folder = processed_base / age_mapping.get(age_group, "age_6_8")
    dest_folder.mkdir(parents=True, exist_ok=True)

    out_path = dest_folder / f"{story_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {out_path}")
    return counter + 1


def main():
    parser = argparse.ArgumentParser(description="Extract metadata from raw story files and save structured JSON.")
    parser.add_argument("--source", default=None, help="Raw subfolder under raw/ to process (e.g., crawler_websites)")
    parser.add_argument("--raw-dir", default="raw", help="Base raw directory")
    parser.add_argument("--processed-dir", default="processed", help="Processed output directory")
    parser.add_argument("--start-id", type=int, default=1, help="Starting counter for WBX IDs")
    args = parser.parse_args()

    raw_base = Path(args.raw_dir)
    processed_base = Path(args.processed_dir)

    if args.source:
        raw_dirs = [raw_base / args.source]
    else:
        # process all subfolders
        raw_dirs = [p for p in raw_base.iterdir() if p.is_dir()]

    counter = args.start_id
    for rd in raw_dirs:
        for txt in sorted(rd.glob("*.txt")):
            try:
                counter = extract_and_save(txt, processed_base, counter)
            except Exception as e:
                print(f"Failed to process {txt}: {e}")


if __name__ == "__main__":
    main()
