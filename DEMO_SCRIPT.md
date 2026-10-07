# 🎬 REX Review Gate - Demo Script

This script is designed for a live hackathon presentation. It guides you from a completely fresh clone of the repository all the way through showcasing REX's core features: Math-based Triage, AI Deep Reviews, PR Ranking, and GitHub CI/CD posting.

---

## Step 1: The Fresh Start (Setup)
*Goal: Prove the app runs instantly and locally.*

**Action:**
1. Clone the repository and enter the directory.
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```
2. Activate a fresh environment and install requirements.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Boot the Streamlit app.
   ```bash
   streamlit run app.py
   ```

**Talking Point:** *"REX is completely local-first. We don't need a heavy database. It runs strictly on your local Git history. Right out of the box, it’s ready to process pull requests offline."*

---

## Step 2: The Core Problem & Architecture (Home Tab)
*Goal: Explain "Math Before AI".*

**Action:**
1. Show the **Home** tab in the Dashboard.
2. Scroll to the **Core Philosophy flowchart**.

**Talking Point:** *"The bottleneck in modern CI/CD isn't just reviewing code, it's wasting expensive AI tokens and senior engineer time on trivial changes. REX solves this using 'Math Before AI'. It intercepts every PR, runs a deterministic Git-history calculation (which costs $0 and runs in milliseconds), and categorizes the PR into Low Risk, High Risk, or Forced Review."*

---

## Step 3: The Risk Tiers (PR Inspector Tab)
*Goal: Show how REX handles different structural complexities.*

**Action:**
1. Click into the **PR Inspector** tab.
2. Click the **🟢 Low Risk** pill.
   - Expand the "Why this score?" table.
   - **Talking Point:** *"Here's a Low Risk PR. The math engine saw a tiny blast radius, no historic bug density, and low entropy. REX didn't even wake up the deep-review AI. It just gives a 2-line summary and a fast-track approval button."*
3. Click the **🟡 High Risk** pill.
   - Open a PR to reveal the Deep Review.
   - **Talking Point:** *"Now look at High Risk. The math engine detected high entropy and missing tests. Here, REX woke up the LLM. It generates a deep analysis, extracts structural findings, and blocks auto-merge pending a senior engineer's approval."*
4. Click the **🔴 Forced Review** pill.
   - Open the PR to show the Secret/Sensitive Path warnings.
   - **Talking Point:** *"Overrides beat math. If REX detects a hardcoded API key or someone touching a sensitive `payments/` directory, it forces a deep AI review immediately, regardless of how small the PR is."*

---

## Step 4: Multi-Agent Ranking (PR Ranking Tab)
*Goal: Show how REX handles overlapping/competing PRs for the same issue.*

**Action:**
1. Switch to the **PR Ranking** tab.
2. Select **Issue #42** (or whichever issue has multiple PRs).

**Talking Point:** *"What happens when two engineers submit a PR for the same Jira ticket? REX ranks them. It evaluates Test Delta, Diff Efficiency, and uses LLM Rubrics to score Architectural Alignment. It even highlights Hallucination-defense verified bugs. This lets the reviewer instantly know which branch to focus their time on."*

---

## Step 5: Economics & Telemetry (Economics Tab)
*Goal: Prove the ROI of the tool.*

**Action:**
1. Switch to the **Economics & ROI** tab.
2. Move the **Enterprise PR Mix Projection slider**.

**Talking Point:** *"Because we use Math Before AI, we don't waste tokens. In our benchmark, filtering out the Low Risk PRs saved us massive amounts of AI compute. This slider shows that at enterprise scale, REX drastically reduces LLM token costs while speeding up deployment."*

---

## Step 6: The Live GitHub Worker (Terminal)
*Goal: Prove REX integrates with live CI/CD pipelines.*

**Action:**
1. Open a new terminal tab (leave the dashboard running).
2. Run the standalone GitHub integration script:
   ```bash
   python rex_github_worker.py
   ```
3. Enter your repository and a live PR number when prompted.
4. Open your GitHub repository in the browser and show the comment live on the PR.

**Talking Point:** *"Finally, REX isn't just a local dashboard. Using our decoupled background worker, REX posts its findings, risk scores, and senior-approval blocks directly back into the GitHub PR as a comment, integrating flawlessly into the developer's natural workflow."*
