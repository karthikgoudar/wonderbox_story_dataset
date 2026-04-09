import json
import os

folder = r"C:\Wonder box\wonderbox_story_dataset\processed\age_3_5"

for file in os.listdir(folder):
    if file.endswith(".json"):
        path = os.path.join(folder, file)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Add story if missing
            if "story" not in data or not data["story"]:
                story_text = " ".join(
                    scene.get("text", "") for scene in data.get("scenes", [])
                ).strip()

                data["story"] = story_text if story_text else "Story content not available."

            # Remove wrong story inside scenes
            for scene in data.get("scenes", []):
                if "story" in scene:
                    del scene["story"]

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"✔ Fixed: {file}")

        except Exception as e:
            print(f"❌ Error in {file}: {e}")