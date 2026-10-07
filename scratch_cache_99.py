import json

with open("demo_cache/summary__pr_pr_typo_fix__default__v1.json", "r") as f:
    cache = json.load(f)

cache["head_sha"] = "671ee44417929b122a2bc90d14c1b7eac5a51a2b"
cache["response"]["summary"] = "This is a lightweight change that touches only the README. No deep inspection is required for this low-risk update."

with open("demo_cache/summary__pr_pr_issue99__default__v1.json", "w") as f:
    json.dump(cache, f, indent=2)

print("Created cache for pr_issue99")
