import os

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
def_idx = -1
home_idx = -1

for i, line in enumerate(lines):
    if line.startswith('# Setup structural placeholders for loading state'):
        start_idx = i
    if line.startswith('def get_git_repo_info():'):
        def_idx = i
    if line.startswith('if selected == "Home":'):
        home_idx = i

if start_idx != -1 and def_idx != -1 and home_idx != -1:
    final_lines = lines[:start_idx]
    
    # 1. Add get_git_repo_info block
    final_lines.extend(lines[def_idx:home_idx])
    
    # 2. Add state machine
    state_machine = """# Initialize state
if "current_tab" not in st.session_state:
    st.session_state.current_tab = selected
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False

# 1. Detect tab change and trigger load state
if st.session_state.current_tab != selected:
    st.session_state.current_tab = selected
    st.session_state.is_loading = True
    st.rerun()

# 2. Render ONLY the loader in isolation
if st.session_state.is_loading:
    st.session_state.is_loading = False
    st.markdown(
        \"\"\"
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 60vh; gap: 15px;">
            <svg style="animation: spin 1s linear infinite; width: 40px; height: 40px; color: #238636;" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-opacity="0.2" stroke-width="2" vector-effect="non-scaling-stroke"></circle>
                <path d="M15 8a7.002 7.002 0 00-7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" vector-effect="non-scaling-stroke"></path>
            </svg>
            <span style="color: #888888; font-size: 14px; font-weight: 500;">Resolving Git deltas...</span>
        </div>
        <style>
            @keyframes spin { 100% { transform: rotate(360deg); } }
            header { visibility: hidden; } /* Hide Streamlit top decoration */
        </style>
        \"\"\",
        unsafe_allow_html=True
    )
    import time
    time.sleep(0.4)
    st.rerun()

# 3. Render the actual tab content ONLY when not loading
else:
"""
    final_lines.append(state_machine)
    
    # 3. Indent routing block
    for line in lines[home_idx:]:
        if line.strip() == "":
            final_lines.append(line)
        else:
            final_lines.append("    " + line)
            
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
    print("Done")
else:
    print("Failed to find indices")
