import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==========================================
# 1. MINIMAL CONFIG
# ==========================================
st.set_page_config(page_title="IronOS", page_icon="⚡", layout="wide")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    class DummyConnection:
        def read(self, **kwargs): return pd.DataFrame()
        def update(self, **kwargs): pass
    conn = DummyConnection()

# Minimal CSS to remove +/- buttons
st.markdown("""
    <style>
    div[data-testid="stNumberInput"] button { display: none !important; }
    .stNumberInput input { text-align: center !important; height: 45px !important; }
    div[data-testid="stNumberInput"] > label { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING (SIMPLIFIED)
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try:
        df_lib = conn.read(worksheet="Master", ttl=0, dtype=str)
        df_profile = conn.read(worksheet="Profile", ttl=0, dtype=str)
    except:
        df_lib = pd.DataFrame()
        df_profile = pd.DataFrame()
    
    if not df_lib.empty:
        df_lib.dropna(how='all', inplace=True)
    else:
        df_lib = pd.DataFrame(columns=['Template', 'Week', 'Day', 'Exercise', 'Sets', 'Reps', 'Pct'])
    
    if not df_profile.empty:
        df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)
    
    return df_lib, df_profile

df_lib, df_profile = load_data()

# ==========================================
# 3. APP LAYOUT - SIMPLE SIDE-BY-SIDE
# ==========================================
st.title("⚡ IronOS")

if 'workout_queue' not in st.session_state:
    st.session_state.workout_queue = []

# Load workout if not loaded
if not st.session_state.workout_queue:
    if not df_lib.empty:
        template = st.selectbox("Template", df_lib['Template'].unique())
        if template:
            week = st.selectbox("Week", df_lib[df_lib['Template'] == template]['Week'].unique())
            if week:
                day = st.selectbox("Day", df_lib[(df_lib['Template'] == template) & (df_lib['Week'] == week)]['Day'].unique())
                if day and st.button("Load Workout"):
                    workout = df_lib[(df_lib['Template'] == template) & 
                                     (df_lib['Week'] == week) & 
                                     (df_lib['Day'] == day)]
                    st.session_state.workout_queue = workout.to_dict('records')
                    st.rerun()

# Display workout if loaded
if st.session_state.workout_queue:
    for i, ex in enumerate(st.session_state.workout_queue):
        with st.expander(f"{ex['Exercise']}", expanded=True):
            sets = int(float(ex.get('Sets', 3)))
            
            # SINGLE HEADER ROW
            header_cols = st.columns([0.1, 0.225, 0.225, 0.225, 0.111, 0.111])
            header_cols[0].markdown("**SET**")
            header_cols[1].markdown("**TARGET**")
            header_cols[2].markdown("**REPS**")
            header_cols[3].markdown("**ACTUAL**")
            header_cols[4].markdown("**REPS**")
            header_cols[5].markdown("**RPE**")
            
            # DATA ROWS
            for s in range(sets):
                # Calculate target weight
                base_max = 0.0
                if not df_profile.empty:
                    lift_match = df_profile[df_profile['Lift'].str.contains(ex['Exercise'], case=False, na=False)]
                    if not lift_match.empty:
                        base_max = float(lift_match.iloc[0]['Max'])
                
                pct = float(ex.get('Pct', 0))
                target_weight = int((base_max * pct) / 5) * 5 if pct > 0 else 0
                target_reps = ex.get('Reps', '5')
                
                # SINGLE ROW FOR EACH SET
                row_cols = st.columns([0.1, 0.225, 0.225, 0.225, 0.111, 0.111])
                
                # Set number
                row_cols[0].markdown(f"**{s+1}**")
                
                # Target weight (display only)
                row_cols[1].markdown(f"<div style='background: #2d3436; color: white; padding: 10px; border-radius: 6px; text-align: center;'>{target_weight}</div>", unsafe_allow_html=True)
                
                # Target reps (display only)
                row_cols[2].markdown(f"<div style='background: #1a5276; color: white; padding: 10px; border-radius: 6px; text-align: center;'>{target_reps}</div>", unsafe_allow_html=True)
                
                # Actual weight input
                w_key = f"w_{i}_{s}"
                if w_key not in st.session_state:
                    st.session_state[w_key] = 0.0
                actual_weight = row_cols[3].number_input(
                    "Weight", 
                    value=st.session_state[w_key],
                    step=5.0,
                    key=w_key,
                    label_visibility="collapsed",
                    format="%d"
                )
                
                # Actual reps input
                r_key = f"r_{i}_{s}"
                if r_key not in st.session_state:
                    st.session_state[r_key] = 0
                actual_reps = row_cols[4].number_input(
                    "Reps",
                    value=st.session_state[r_key],
                    step=1,
                    key=r_key,
                    label_visibility="collapsed",
                    format="%d"
                )
                
                # RPE input
                rpe_key = f"rpe_{i}_{s}"
                if rpe_key not in st.session_state:
                    st.session_state[rpe_key] = 0.0
                rpe = row_cols[5].number_input(
                    "RPE",
                    value=st.session_state[rpe_key],
                    step=0.5,
                    key=rpe_key,
                    label_visibility="collapsed",
                    format="%.1f"
                )
    
    if st.button("Save Workout"):
        st.success("Workout saved!")
        st.session_state.workout_queue = []
        st.rerun()