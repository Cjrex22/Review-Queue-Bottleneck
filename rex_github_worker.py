import os
import requests
import sys

def post_rex_comment(repo, pr_number, token):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # This simulates the payload REX generates after a deep review
    comment_body = """### 🦖 REX Automated Triage: FORCED REVIEW
**Math Before AI Engine:** 🔴 High Structural Risk Detected

REX has completed a deep-dive analysis on this diff. 

**Key Findings:**
* 🛑 **Critical:** A hardcoded secret/API key was detected in the configuration files.
* ⚠️ **Warning:** The blast radius of this PR touches 3 core authentication modules.
* 🛡️ **Action Required:** This PR has been flagged for mandatory human Senior Engineer approval. Auto-merge is disabled.

*View the full severity ranking and token economics in the [REX Dashboard](http://localhost:8501).*"""

    payload = {"body": comment_body}
    
    print(f"🚀 REX Background Worker initiated...")
    print(f"📡 Connecting to GitHub API for {repo} PR #{pr_number}...")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print("✅ Success! REX review successfully posted to the live GitHub PR.")
        print(f"🔗 View comment: {response.json().get('html_url')}")
    else:
        print(f"❌ Failed to post comment. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("--- REX GitHub Integration Worker ---")
    repo = input("Enter target repo (e.g., your-username/your-repo): ")
    pr_num = input("Enter PR number (e.g., 1): ")
    token = input("Enter GitHub Personal Access Token: ")
    
    if repo and pr_num and token:
        post_rex_comment(repo, pr_num, token)
    else:
        print("Missing required inputs.")
