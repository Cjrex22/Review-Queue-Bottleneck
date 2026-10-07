import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the PR name span with an a tag
old_span = '<span style="font-weight: 600; font-size: 15px; color: #e6edf3;">{pr_name}</span>'
new_span = '<a href="?pr_details={pr_name}" target="_self" style="font-weight: 600; font-size: 15px; color: #e6edf3; text-decoration: none;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{pr_name}</a>'

content = content.replace(old_span, new_span)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
