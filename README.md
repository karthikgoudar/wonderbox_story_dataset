# WonderBox Story Dataset

This repository contains the dataset pipeline for collecting and processing children's stories used to fine-tune the WonderBox storytelling model.

Workflow

1. Collect raw stories
   Use `scripts/crawler.py` or manually add text files into `raw/<source>/`.

2. Clean the text
   Remove ads, navigation text, and unrelated content from the raw file.

3. Extract metadata
   Run `scripts/metadata_extractor.py` to generate structured JSON metadata.

4. Generate scene image prompts
   For each scene, generate a child-friendly illustration prompt using the
   `prompts/image_prompt_template.txt` template.

5. Save processed story
   Save the final structured JSON into `processed/age_3_5`, `processed/age_6_8`,
   or `processed/age_9_12`.

6. Validate dataset
   Run `scripts/dataset_validator.py` to ensure:
   - required fields exist
   - exactly 5 scenes exist
   - each scene has an image_prompt

7. Commit dataset
   Add the JSON file to git and update `dataset_stats.json`.

Contributor instructions (Siri and Akshatha)

- To add a new story from a webpage:
  - Run `scripts/crawler.py --url <STORY_URL> --source crawler_websites` to save the raw text.
  - Inspect and clean the saved file under `raw/` as needed.
  - Run `scripts/metadata_extractor.py --source crawler_websites` to generate processed JSON.
  - Run `scripts/dataset_validator.py` and fix any reported issues.
  - Update `dataset_stats.json` and open a PR.

- To add a local story file manually:
  - Place the `.txt` file into the appropriate `raw/<source>/` folder.
  - Continue with metadata extraction and validation as above.

Notes for reviewers

- Processed stories live in `processed/age_3_5`, `processed/age_6_8`, and `processed/age_9_12`.
- Each processed story is a single JSON file that follows the project schema with the name `WBX_3-5_000001...`.
