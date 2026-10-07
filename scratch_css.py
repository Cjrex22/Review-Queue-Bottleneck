with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the aggressive CSS
old_css = """    html, body, [class*="css"], [class*="st-"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji" !important;
    }
    
    /* Restore Streamlit icons that use ligatures */
    .stIcon, .material-icons, .material-symbols-rounded, [data-testid="stIconMaterial"] {
        font-family: "Material Symbols Rounded" !important;
    }"""

new_css = """    /* Apply GitHub's native system font stack but protect icons */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
    }
    
    div[class*="st-"]:not(.stIcon):not(.material-icons):not(.material-symbols-rounded):not([data-testid="stIconMaterial"]):not(svg):not(path) {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
    }
    
    /* Safely force Material icons back where Streamlit uses them */
    .stIcon, .material-icons, .material-symbols-rounded, [data-testid="stIconMaterial"], [data-testid="stExpanderToggleIcon"] {
        font-family: "Material Symbols Rounded" !important;
    }"""

content = content.replace(old_css, new_css)
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
