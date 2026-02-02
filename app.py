import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==========================================
# 1. CONFIG & "APP-LIKE" CSS
# ==========================================
st.set_page_config(page_title="IronOS", page_icon="⚡", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("""
    <style>
        /* 1. TIGHTER SPACING */
        .block-container {
            padding-top: 1rem; 
            padding-bottom: 2rem; 
            padding-left: 0.5rem; 
            padding-right: 0.5rem;
        }
        
        /* 2. CUSTOM INPUT BOXES (Look like the screenshot) */
        .stNumberInput input {
            height: 40px; 
            text-align: center; 
            font-weight: bold;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        
        /* 3. HIDE LABEL SPACE */
        div[data-baseweb="select"] > div {min-height: 40px;}
        .stNumberInput label {display: none;} /* Brutally hide labels for grid look */
        
        /* 4. EXPANDER STYLING (The Gray Bars) */
        .streamlit-expanderHeader {
            background-color: #f0f2f6;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-weight: bold;
            color: #31333F;
        }
        
        /* 5. TARGET BOX STYLING (Visual only) */
        .target-box {
            background-color: #ffffff;
            border: 1px solid #ccc;
            border-radius: 5px;
            text-align: center;
            padding: 8px 0;
            color: #555;
            font-weight: bold;
            font-size: 1rem;
            margin-bottom: 10px;
        }
        
        .arrow-box {
            text-align: center;
            font-size: 1.5rem;
            padding-top: 2px;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING
# ==========================================
@st.cache_data(ttl=600)
def load_static_data():
    df_lib = pd.DataFrame(); df_profile = pd.DataFrame(); df_dir = pd.DataFrame()
    rpe_dict = {10: {1: 1.0}}

    try: df_lib = conn.read(worksheet="Master", ttl=0, dtype=str)
    except: pass
    try: df_profile = conn.read(worksheet="Profile", ttl=0, dtype=str)
    except: pass
    try: df_dir = conn.read(worksheet="Directory", ttl=0, dtype=str)
    except: pass
    try:
        df_const = conn.read(worksheet="Constants", ttl=0, dtype=str)
        if not df_const.empty:
            rpe_dict = {}
            for _, row in df_const.iterrows():
                try:
                    r = float(str(row['RPE']).strip())
                    rpe_dict[r] = {}
                    for c in df_const.columns:
                        if c != 'RPE' and str(c).isdigit():
                            rpe_dict[r][int(c)] = float(str(row[c]).strip())
                except: continue
    except: pass
            
    # Cleanup
    if not df_lib.empty:
        df_lib.dropna(how='all', inplace=True)
        df_lib['Sets'] = pd.to_numeric(df_lib['Sets'], errors='coerce').fillna(0).astype(int)
        df_lib['Pct'] = pd.to_numeric(df_lib['Pct'], errors='coerce').fillna(0.0)
    if not df_profile.empty:
        df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)
            
    return df_lib, df_profile, df_dir, rpe_dict

def get_profile_max(df_profile, lift_name):
    if df_profile.empty: return 0.0
    lift_name = lift_name.lower()
    for _, row in df_profile.iterrows():
        p_lift = str(row.get('Lift', '')).lower()
        if p_lift in lift_name:
            try: return float(row.get('Max', 0))
            except: return 0.0
    return 0.0

# --- SIDEBAR & LOAD ---
with st.sidebar:
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
df_lib, df_profile, df_dir, RPE_DATA = load_static_data()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
if 'workout_queue' not in st.session_state: st.session_state.workout_queue = []

def copy_plan_to_actual(index, sets):
    ex = st.session_state.workout_queue[index]
    guide = ex.get('Guide_Weight', 0)
    for s in range(sets):
        st.session_state[f"w_{index}_{s}"] = float(guide)
        try: st.session_state[f"r_{index}_{s}"] = int(str(ex['Reps']).replace("+", "").strip())
        except: st.session_state[f"r_{index}_{s}"] = 5

# ==========================================
# 4. UI: THE "LOGBOOK" HEADER
# ==========================================
# Top Bar: Date + Actions
c_head_1, c_head_2, c_head_3 = st.columns([1, 2, 1])
c_head_1.button("⬅ Back") # Placeholder
c_head_2.markdown(f"<h3 style='text-align: center; margin: 0;'>{date.today().strftime('%b %d')} 📝</h3>", unsafe_allow_html=True)
c_head_3.button("Add Lift +") # Placeholder

st.markdown("---")

# ==========================================
# 5. UI: WORKOUT BUILDER (Hidden if Active)
# ==========================================
if not st.session_state.workout_queue:
    # ... (Same Builder Logic as before, just kept compact) ...
    templates = []
    if not df_lib.empty and 'Template' in df_lib.columns:
        templates = sorted(list(df_lib['Template'].unique()))
    if "Custom Build" not in templates: templates.insert(0, "Custom Build")
    
    sel_temp = st.selectbox("Select Program", templates, index=None, placeholder="Choose Mission...")

    if sel_temp == "Custom Build":
        list_profile = df_profile['Lift'].unique().tolist() if not df_profile.empty and 'Lift' in df_profile.columns else []
        list_lib = df_lib['Exercise'].unique().tolist() if not df_lib.empty and 'Exercise' in df_lib.columns else []
        list_dir = df_dir['Exercise'].unique().tolist() if not df_dir.empty and 'Exercise' in df_dir.columns else []
        all_exercises = sorted(list(set(list_profile + list_lib + list_dir)))
        
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        new_ex = c1.selectbox("Exercise", all_exercises, index=None, label_visibility="collapsed", placeholder="Lift")
        new_sets = c2.number_input("Sets", min_value=1, value=3, label_visibility="collapsed")
        new_reps = c3.text_input("Reps", value="5", label_visibility="collapsed")
        if c4.button("Add"):
             if 'builder_queue' not in st.session_state: st.session_state.builder_queue = []
             st.session_state.builder_queue.append({
                "Category": "Custom", "Exercise": new_ex, "Sets": new_sets, "Reps": new_reps, "Guide_Weight": 0, "Meta": {"Template": "Custom"}
             })
             st.rerun()
        
        if 'builder_queue' in st.session_state and st.session_state.builder_queue:
            for q in st.session_state.builder_queue:
                st.caption(f"• {q['Exercise']} ({q['Sets']} x {q['Reps']})")
            if st.button("🚀 Start Workout", type="primary", use_container_width=True):
                st.session_state.workout_queue = st.session_state.builder_queue
                del st.session_state.builder_queue
                st.rerun()

    elif sel_temp:
        # Standard Template Loading Logic
        weeks = sorted(df_lib[df_lib['Template'] == sel_temp]['Week'].unique())
        sel_week = st.selectbox("Week", weeks, index=None)
        if sel_week:
            days = sorted(df_lib[(df_lib['Template'] == sel_temp) & (df_lib['Week'] == sel_week)]['Day'].unique())
            sel_day = st.selectbox("Day", days, index=None)
            if sel_day and st.button("🚀 GO", type="primary", use_container_width=True):
                rows = df_lib[(df_lib['Template'] == sel_temp) & (df_lib['Week'] == sel_week) & (df_lib['Day'] == sel_day)]
                st.session_state.workout_queue = []
                for _, row in rows.iterrows():
                    base_max = get_profile_max(df_profile, row['Exercise'])
                    pct = float(row['Pct'])
                    guide = int((base_max * pct) / 5) * 5 if pct > 0 else 0
                    st.session_state.workout_queue.append({
                        "Category": str(row.get('Category', 'Accessory')),
                        "Exercise": row['Exercise'],
                        "Sets": int(row['Sets']),
                        "Reps": str(row['Reps']),
                        "Guide_Weight": guide,
                        "Meta": {"Template": sel_temp}
                    })
                st.rerun()

# ==========================================
# 6. UI: THE "SCREENSHOT MATCH" GRID
# ==========================================
if st.session_state.workout_queue:
    logs_to_save = []

    if st.button("Clear Session"): st.session_state.workout_queue = []; st.rerun()
    
    for i, ex in enumerate(st.session_state.workout_queue):
        
        # --- THE CARD HEADER (Matches the Gray Bar) ---
        # We use an expander to allow collapsing, defaulting to TRUE (Open)
        with st.expander(f"**{ex['Exercise']}** (Sets: {ex['Sets']})", expanded=True):
            
            # COPY BUTTON (Small, like the clipboard icon)
            if st.button("📋 Fill All Targets", key=f"cp_{i}", help="Copy Targets to Actuals"):
                copy_plan_to_actual(i, ex['Sets'])
                st.rerun()

            # --- COLUMN HEADERS ---
            # Layout: [Target Weight] [Target Reps] [Arrow] [Actual Weight] [Actual Reps] [RPE]
            h1, h2, h3, h4, h5, h6 = st.columns([1.2, 0.8, 0.5, 1.2, 0.8, 0.8])
            h1.caption("Target")
            h2.caption("Reps")
            h4.caption("Actual")
            h5.caption("Reps")
            h6.caption("RPE")
            
            # --- THE SET ROWS ---
            for s in range(ex['Sets']):
                c1, c2, c3, c4, c5, c6 = st.columns([1.2, 0.8, 0.5, 1.2, 0.8, 0.8])
                
                # 1. Target (Visual Box)
                c1.markdown(f"<div class='target-box'>{ex['Guide_Weight']}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='target-box'>{ex['Reps']}</div>", unsafe_allow_html=True)
                
                # 2. Arrow
                c3.markdown("<div class='arrow-box'>🟩</div>", unsafe_allow_html=True)
                
                # 3. Actual Inputs (Styled to look like boxes)
                w = c4.number_input(f"w{s}", value=0.0, step=5.0, key=f"w_{i}_{s}", label_visibility="collapsed")
                r = c5.number_input(f"r{s}", value=0, step=1, key=f"r_{i}_{s}", label_visibility="collapsed")
                rpe = c6.number_input(f"rpe{s}", value=0.0, step=0.5, key=f"rpe_{i}_{s}", label_visibility="collapsed")
                
                logs_to_save.append({
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Exercise": ex['Exercise'],
                    "Set": s+1, "Weight": w, "Reps": r, "RPE": rpe
                })
            
            # --- FOOTER STATS (Placeholder for now) ---
            st.caption(f"📊 **Est 1RM:** {ex['Guide_Weight']*1.1:.0f} lbs  |  **Vol:** {ex['Sets']*ex['Guide_Weight']*5} lbs")

    # SAVE
    st.markdown("---")
    if st.button("✅ Finish Workout", type="primary", use_container_width=True):
        new_logs = pd.DataFrame(logs_to_save)
        new_logs = new_logs[new_logs['Weight'] > 0]
        if not new_logs.empty:
            try:
                current_logs = conn.read(worksheet="Logs", ttl=0, dtype=str)
                updated = pd.concat([current_logs, new_logs], ignore_index=True)
                conn.update(worksheet="Logs", data=updated)
                st.toast("Saved!", icon="🔥")
                st.session_state.workout_queue = []
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Log some lifts first.")
