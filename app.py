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

# CSS to remove +/- buttons and force horizontal layout
st.markdown("""
    <style>
    div[data-testid="stNumberInput"] button { display: none !important; }
    .stNumberInput input { 
        text-align: center !important; 
        height: 45px !important;
        width: 100% !important;
    }
    div[data-testid="stNumberInput"] > label { display: none !important; }
    
    /* Force columns to be compact */
    [data-testid="column"] {
        padding: 0 2px !important;
        min-width: 0 !important;
    }
    
    /* Make horizontal rows */
    .horizontal-row {
        display: flex;
        flex-direction: row;
        width: 100%;
        margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING
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
# 3. APP LAYOUT
# ==========================================
st.title("⚡ IronOS")

if 'workout_queue' not in st.session_state:
    st.session_state.workout_queue = []

# Load workout if not loaded
if not st.session_state.workout_queue:
    if not df_lib.empty and 'Template' in df_lib.columns:
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
    else:
        st.warning("No workout templates found.")

# Display workout if loaded
if st.session_state.workout_queue:
    logs_to_save = []
    
    for i, ex in enumerate(st.session_state.workout_queue):
        with st.expander(f"{ex.get('Exercise', 'Exercise')}", expanded=True):
            try:
                sets = int(float(ex.get('Sets', 3)))
            except:
                sets = 3
            
            # HEADER - Single row
            cols = st.columns([0.08, 0.23, 0.23, 0.23, 0.115, 0.115])
            cols[0].markdown("**SET**", help="Set number")
            cols[1].markdown("**TARGET**", help="Target weight")
            cols[2].markdown("**REPS**", help="Target reps")
            cols[3].markdown("**ACTUAL**", help="Actual weight")
            cols[4].markdown("**REPS**", help="Actual reps")
            cols[5].markdown("**RPE**", help="RPE rating")
            
            # DATA ROWS - One row per set
            for s in range(sets):
                # Calculate target weight
                base_max = 0.0
                if not df_profile.empty and 'Lift' in df_profile.columns:
                    exercise_name = str(ex.get('Exercise', '')).lower()
                    for _, row in df_profile.iterrows():
                        if str(row.get('Lift', '')).lower() in exercise_name:
                            try:
                                base_max = float(row.get('Max', 0))
                                break
                            except:
                                pass
                
                try:
                    pct = float(ex.get('Pct', 0))
                except:
                    pct = 0
                
                target_weight = int((base_max * pct) / 5) * 5 if pct > 0 else 0
                target_reps = str(ex.get('Reps', '5')).replace('+', '')
                
                # SINGLE ROW FOR THIS SET
                row_cols = st.columns([0.08, 0.23, 0.23, 0.23, 0.115, 0.115])
                
                # Set number
                row_cols[0].markdown(f"**{s+1}**")
                
                # Target weight (display)
                row_cols[1].markdown(
                    f"<div style='background: #2d3436; color: white; padding: 10px 5px; border-radius: 6px; text-align: center; font-weight: bold;'>{target_weight}</div>", 
                    unsafe_allow_html=True
                )
                
                # Target reps (display)
                row_cols[2].markdown(
                    f"<div style='background: #1a5276; color: white; padding: 10px 5px; border-radius: 6px; text-align: center; font-weight: bold;'>{target_reps}</div>", 
                    unsafe_allow_html=True
                )
                
                # Actual weight input - FIXED: Use int for weight to avoid float warning
                w_key = f"w_{i}_{s}"
                if w_key not in st.session_state:
                    st.session_state[w_key] = 0  # Changed to int
                actual_weight = row_cols[3].number_input(
                    f"weight_{i}_{s}",
                    value=int(st.session_state[w_key]),  # Convert to int
                    min_value=0,
                    max_value=1000,
                    step=5,
                    key=w_key,
                    label_visibility="collapsed"
                )
                st.session_state[w_key] = actual_weight  # Store as int
                
                # Actual reps input - FIXED: Use int
                r_key = f"r_{i}_{s}"
                if r_key not in st.session_state:
                    st.session_state[r_key] = 0  # int
                actual_reps = row_cols[4].number_input(
                    f"reps_{i}_{s}",
                    value=int(st.session_state[r_key]),  # Convert to int
                    min_value=0,
                    max_value=100,
                    step=1,
                    key=r_key,
                    label_visibility="collapsed"
                )
                st.session_state[r_key] = actual_reps  # Store as int
                
                # RPE input - Use float for decimals
                rpe_key = f"rpe_{i}_{s}"
                if rpe_key not in st.session_state:
                    st.session_state[rpe_key] = 0.0  # float
                rpe = row_cols[5].number_input(
                    f"rpe_{i}_{s}",
                    value=float(st.session_state[rpe_key]),  # float
                    min_value=0.0,
                    max_value=10.0,
                    step=0.5,
                    key=rpe_key,
                    label_visibility="collapsed",
                    format="%.1f"  # Only format RPE with decimals
                )
                st.session_state[rpe_key] = rpe
                
                # Store log entry
                logs_to_save.append({
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Exercise": ex.get('Exercise', ''),
                    "Set": s + 1,
                    "Weight": actual_weight,  # Already int
                    "Reps": actual_reps,      # Already int
                    "RPE": rpe
                })
                
                # Add a tiny spacer between rows
                if s < sets - 1:
                    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    if col1.button("📋 Fill Targets"):
        # Simple fill function: copy targets to actuals
        for i, ex in enumerate(st.session_state.workout_queue):
            try:
                sets = int(float(ex.get('Sets', 3)))
            except:
                sets = 3
            
            base_max = 0.0
            if not df_profile.empty and 'Lift' in df_profile.columns:
                exercise_name = str(ex.get('Exercise', '')).lower()
                for _, row in df_profile.iterrows():
                    if str(row.get('Lift', '')).lower() in exercise_name:
                        try:
                            base_max = float(row.get('Max', 0))
                            break
                        except:
                            pass
            
            try:
                pct = float(ex.get('Pct', 0))
            except:
                pct = 0
            
            target_weight = int((base_max * pct) / 5) * 5 if pct > 0 else 0
            
            for s in range(sets):
                w_key = f"w_{i}_{s}"
                st.session_state[w_key] = target_weight
                
                r_key = f"r_{i}_{s}"
                target_reps = str(ex.get('Reps', '5')).replace('+', '')
                try:
                    st.session_state[r_key] = int(target_reps)
                except:
                    st.session_state[r_key] = 5
        st.rerun()
    
    if col2.button("✅ Save Workout", type="primary"):
        # Filter out empty entries
        valid_logs = [log for log in logs_to_save if log['Weight'] > 0]
        
        if valid_logs:
            new_logs = pd.DataFrame(valid_logs)
            try:
                # Read existing logs
                current_logs = conn.read(worksheet="Logs", ttl=0, dtype=str)
                if current_logs.empty:
                    current_logs = pd.DataFrame(columns=["Date", "Exercise", "Set", "Weight", "Reps", "RPE"])
                
                # Append new logs
                updated_logs = pd.concat([current_logs, new_logs], ignore_index=True)
                
                # Save to Google Sheets
                conn.update(worksheet="Logs", data=updated_logs)
                
                st.success("Workout saved! ✅")
                st.session_state.workout_queue = []
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {str(e)[:100]}")
        else:
            st.warning("No data to save. Enter at least one set.")