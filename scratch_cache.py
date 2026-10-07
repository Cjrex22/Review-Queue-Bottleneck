import json
import glob

low_summary = "This is a lightweight change that touches only non-critical UI comment files or isolated logic. It introduces a minor functional adjustment without impacting the core system paths. No deep inspection is required for this low-risk update."

high_summary = "This pull request introduces a substantial architectural refactor that heavily modifies the reporting service logic. It touches a massive number of files and lines, fundamentally altering the way data structures are handled throughout the component. Because of the broad blast radius and high churn, the mathematical risk engine has flagged this for a mandatory senior review. Please ensure the structural changes align perfectly with our long-term design patterns before signing off. Extra caution should be exercised regarding the new placeholder implementations."

forced_summary = "This pull request modifies sensitive pathways or introduces hardcoded credentials that directly trigger our security overrides. Because a critical security rule fired, this code cannot be merged without explicit sign-off from a senior reviewer."

for file_path in glob.glob("demo_cache/*.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if "response" in data and "summary" in data["response"]:
        # Determine which to use based on file name or content
        if "summary__pr_" in file_path:
            # Low Risk
            data["response"]["summary"] = low_summary
        elif "deep__pr_" in file_path:
            # Check if it's forced or high risk
            # For simplicity, if it's secret_leak or auth_change, it's forced.
            if "secret_leak" in file_path or "auth_change" in file_path:
                data["response"]["summary"] = forced_summary
            else:
                data["response"]["summary"] = high_summary
                
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

print("Cache updated")
