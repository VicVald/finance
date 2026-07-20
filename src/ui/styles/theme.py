import streamlit as st

CUSTOM_CSS = """
<style>
:root {
    --color-primary: #6290C3;     /* Dusty Denim */
    --color-secondary: #C2E7DA;   /* Frozen Water */
    --color-background: #FFFCF4;  /* Light Beige */
    --color-dark: #1A1B41;        /* Space Indigo */
    --color-accent: #FFC62D;      /* Mustard Yellow */
}

/* Base Background */
.stApp {
    background-color: var(--color-background);
}

/* Text Colors */
h1, h2, h3, h4, h5, h6, p, span {
    color: var(--color-dark) !important;
}

/* Sidebar Styling */
[data-testid="stSidebar"] {
    background-color: var(--color-dark) !important;
}
[data-testid="stSidebar"] * {
    color: white !important;
}

/* Primary Buttons */
.stButton > button {
    background-color: var(--color-primary) !important;
    color: white !important;
    border: none !important;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    background-color: var(--color-dark) !important;
    color: var(--color-accent) !important;
}

/* Metric Cards Custom Styling */
div[data-testid="metric-container"] {
    background-color: white;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    border: 1px solid var(--color-secondary);
}
div[data-testid="metric-container"] label {
    color: var(--color-primary) !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: var(--color-dark) !important;
}

/* Floating Chat Popover Override */
/* Streamlit 1.34+ st.popover usa data-testid="stPopover" */
div[data-testid="stPopover"] {
    position: fixed !important;
    bottom: 2rem !important;
    right: 2rem !important;
    left: auto !important;
    z-index: 9999 !important;
    width: auto !important;
}
div[data-testid="stPopover"] > button {
    background-color: #475569 !important; /* Neutral slate gray */
    color: white !important;
    border-radius: 50% !important;
    width: 60px !important;
    height: 60px !important;
    padding: 0 !important;
    font-size: 24px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    border: none !important;
    transition: none !important;
}
div[data-testid="stPopover"] > button:hover {
    background-color: #475569 !important; /* Remove hover effect */
    transform: none !important;
    color: white !important;
}

</style>
"""

def inject_styles():
    """Injeta a folha de estilos global baseada na ADR-006."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
