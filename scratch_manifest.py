import json

with open("data/manifest.json", "r") as f:
    manifest = json.load(f)

manifest["prs"].append({
    "branch": "pr_issue99",
    "head_sha": "a3cd752a6e89dd06f99ac15c6317736c487c3b92", # just use base_sha or anything valid in fixture
    "title": "Fix README",
    "body": "Fixes #99",
    "issue": "99"
})

with open("data/manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print("Added issue 99")
