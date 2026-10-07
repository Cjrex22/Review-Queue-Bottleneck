import json

with open("data/manifest.json", "r") as f:
    manifest = json.load(f)

for pr in manifest["prs"]:
    if pr["branch"] == "pr_issue99":
        pr["head_sha"] = "671ee44417929b122a2bc90d14c1b7eac5a51a2b"

with open("data/manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print("Updated SHA")
