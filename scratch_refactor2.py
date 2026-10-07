import os

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
skip = False
i = 0
while i < len(lines):
    line = lines[i]
    if 'pr_tab = option_menu(' in line:
        indent = line[:len(line) - len(line.lstrip())]
        out_lines.append(indent + 'active_tab = st.session_state.get("pr_tier_menu", "Low Risk")\n')
        out_lines.append(indent + 'tab_color = "#238636" # green\n')
        out_lines.append(indent + 'if active_tab == "High Risk":\n')
        out_lines.append(indent + '    tab_color = "#d29922" # yellow\n')
        out_lines.append(indent + 'elif active_tab == "Forced Review":\n')
        out_lines.append(indent + '    tab_color = "#f85149" # red\n\n')
        out_lines.append(line)
        i += 1
        continue
    
    if '"nav-link-selected": {"background-color": "#238636"' in line:
        line = line.replace('"#238636"', 'tab_color')
        out_lines.append(line)
        i += 1
        continue
        
    if 'event = st.dataframe(' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_block = f"""{indent}# Filter data based on the selected tab
{indent}# Note: Assuming your dataframe has a 'Tier' column containing these keywords as seen in the UI
{indent}if pr_tab == "Low Risk":
{indent}    filtered_df = df[df['Tier'].str.contains("LOW RISK", case=False, na=False)]
{indent}elif pr_tab == "High Risk":
{indent}    filtered_df = df[df['Tier'].str.contains("HIGH RISK", case=False, na=False)]
{indent}else:
{indent}    filtered_df = df[df['Tier'].str.contains("FORCED REVIEW", case=False, na=False)]
{indent}    
{indent}# Render the filtered table (Temporary until next UI iteration)
{indent}if not filtered_df.empty:
{indent}    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
{indent}else:
{indent}    st.info(f"No {{pr_tab.lower()}} pull requests in the queue.")\n"""
        out_lines.append(new_block)
        
        # Skip until the end of this block (which is elif selected == "PR Ranking":)
        while i < len(lines):
            if 'elif selected == "PR Ranking":' in lines[i]:
                out_lines.append('\n')
                out_lines.append(lines[i])
                break
            i += 1
        i += 1
        continue
        
    out_lines.append(line)
    i += 1

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(out_lines)
print("Done")
