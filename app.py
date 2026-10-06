import streamlit as st
import json
import pandas as pd
from pathlib import Path
from rex.risk import calculate_risk

st.set_page_config(page_title="REX Review Gate", layout="wide")
st.title("REX Review Gate")

repo = Path("data/fixture_repo")
manifest_path = Path("data/manifest.json")

if manifest_path.exists():
    with open(manifest_path) as f:
        manifest = json.load(f)
        
    data = []
    for pr in manifest["prs"]:
        res = calculate_risk(repo, pr["branch"], pr["title"], pr["body"])
        data.append({
            "Branch": pr["branch"],
            "Risk Score": res.risk_score,
            "Label": res.label,
            "Overrides": ", ".join(res.overrides.reasons) if res.overrides.reasons else "-",
            "Injection": res.overrides.injection_detected
        })
        
    st.table(pd.DataFrame(data))
else:
    st.error("Manifest not found.")
