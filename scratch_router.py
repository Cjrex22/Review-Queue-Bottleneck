import sys
with open("rex/router.py", "r") as f:
    content = f.read()

old_logic = """    if counterfactual:
        task = "counterfactual_deep"
        prompt = DEEP_PROMPT.format(data=data_text)
    elif risk.tier == "LOW" and not force_deep:
        task = "summary"
        prompt = SUMMARY_PROMPT.format(data=data_text)
    else:
        task = "deep"
        prompt = DEEP_PROMPT.format(data=data_text)"""

new_logic = """    if counterfactual:
        task = "counterfactual_deep"
        prompt = DEEP_PROMPT.format(data=data_text, summary_length="4-5 lines")
    elif risk.tier == "LOW" and not force_deep:
        task = "summary"
        prompt = SUMMARY_PROMPT.format(data=data_text)
    else:
        task = "deep"
        if risk.overrides.reasons:
            s_len = "2-3 lines"
        else:
            s_len = "4-5 lines"
        prompt = DEEP_PROMPT.format(data=data_text, summary_length=s_len)"""

content = content.replace(old_logic, new_logic)

with open("rex/router.py", "w") as f:
    f.write(content)
