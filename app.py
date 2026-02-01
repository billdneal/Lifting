import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==========================================
# 1. COMPACT CONFIG & CSS
# ==========================================
st.set_page_config(page_title="IronOS", page_icon="⚡", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 2rem; padding-left: 1rem; padding-right: 1rem;}
        div[data-testid="stExpander"] div[role="button"] p {font-size: 1rem; font-weight: bold;}
        .stNumberInput input {height: 35px; font-size: 0.9rem;} 
        div[data-baseweb="select"] > div {min-height: 35px;}
        button {height: 38px; padding-top: 0px !important; padding-bottom: 0px !important;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING (SAFE MODE)
# ==========================================
@st.cache_data(ttl=600)
def load_rpe_table():
    try:
        df = conn.read(worksheet="Constants", ttl=0, dtype=str)
        rpe_dict = {}
        for _, row in df.iterrows():
            rpe_val_str = str(row['RPE']).strip()
            if not rpe_val_str or rpe_val_str.lower() == 'nan': continue
            rpe_val = float(rpe_val_str)
            rpe_dict[rpe_val] = {}
            for c in df.columns:
                if c != 'RPE' and str(c).isdigit():
                    val = str(row[c]).strip()
                    if val and val.lower() != 'nan':
                         rpe_dict[rpe_val][int(c)] = float(val)
        return rpe_dict
    except: return {10: {1: 1.0}} 

def get_profile_max(df_profile, lift_name):
    if df_profile.empty: return 0.0
    lift_name = lift_name.lower()
    for _, row in df_profile.iterrows():
        p_lift = str(row.get('Lift', '')).lower()
        if p_lift in lift_name:
            try: return float(row.get('Max', 0))
            except: return 0.0
    return 0.0

try:
    # Added "Directory" to the load list
    df_lib = conn.read(worksheet="Master", ttl=0, dtype=str)
    df_logs = conn.read(worksheet="Logs", ttl=0, dtype=str)
    df_profile = conn.read(worksheet="Profile", ttl=0, dtype=str)
    df_dir = conn.read(worksheet="Directory", ttl=0, dtype=str) # NEW!
    RPE_DATA = load_rpe_table()
    
    # Safe Conversions
    if not df_lib.empty:
        df_lib.dropna(how='all', inplace=True)
        df_lib['Sets'] = pd.to_numeric(df_lib['Sets'], errors='coerce').fillna(0).astype(int)
        df_lib['Pct'] = pd.to_numeric(df_lib['Pct'], errors='coerce').fillna(0.0)
    if not df_profile.empty:
        df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)

except Exception as e:
    st.error(f"Data Load Error: {e}"); st.stop()

# ==========================================
# 3. SESSION LOGIC
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
# 4. COMPACT UI
# ==========================================
st.caption("⚡ IronOS Command")

# --- A. SELECTOR / BUILDER ---
if not st.session_state.workout_queue:
    
    templates = list(df_lib['Template'].unique()) if not df_lib.empty else []
    if "Custom Build" not in templates: templates.insert(0, "Custom Build")
    
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    sel_temp = c1.selectbox("Program", templates, index=None, label_visibility="collapsed", placeholder="Select Program...")

    # --- MODE 1: STANDARD TEMPLATE ---
    if sel_temp and sel_temp != "Custom Build":
        weeks = sorted(df_lib[df_lib['Template'] == sel_temp]['Week'].unique())
        sel_week = c2.selectbox("Week", weeks, index=None, label_visibility="collapsed", placeholder="Week...")
        
        if sel_week:
            days = sorted(df_lib[(df_lib['Template'] == sel_temp) & (df_lib['Week'] == sel_week)]['Day'].unique())
            sel_day = c3.selectbox("Day", days, index=None, label_visibility="collapsed", placeholder="Day...")
            
            if sel_day:
                if c4.button("🚀 GO", type="primary", use_container_width=True):
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
                            "RPE_Target": str(row.get('RPE', '')),
                            "Guide_Weight": guide,
                            "Meta": {"Template": sel_temp, "Week": sel_week, "Day": sel_day}
                        })
                    st.rerun()

    # --- MODE 2: CUSTOM BUILDER ---
    elif sel_temp == "Custom Build":
        # MERGE LISTS: Profile + Master + Directory
        list_profile = df_profile['Lift'].unique().tolist() if not df_profile.empty else []
        list_lib = df_lib['Exercise'].unique().tolist() if not df_lib.empty else []
        list_dir = df_dir['Exercise'].unique().tolist() if 'df_dir' in locals() and not df_dir.empty else []
        
        # Combine and Sort
        all_exercises = sorted(list(set(list_profile + list_lib + list_dir)))
        
        st.info("🛠️ **Custom Builder Active**")
        b1, b2, b3, b4 = st.columns([2, 1, 1, 1])
        
        new_ex = b1.selectbox("Exercise", all_exercises, index=None, placeholder="Pick Lift")
        new_sets = b2.number_input("Sets", min_value=1, value=3)
        new_reps = b3.text_input("Reps", value="5")
        
        if b4.button("Add +"):
            if new_ex:
                if 'builder_queue' not in st.session_state: st.session_state.builder_queue = []
                st.session_state.builder_queue.append({
                    "Category": "Custom",
                    "Exercise": new_ex,
                    "Sets": new_sets,
                    "Reps": new_reps,
                    "Guide_Weight": 0,
                    "Meta": {"Template": "Custom", "Week": 1, "Day": 1}
                })
                st.rerun()
        
        if 'builder_queue' in st.session_state and st.session_state.builder_queue:
            st.markdown("---")
            for q in st.session_state.builder_queue:
                st.text(f"• {q['Exercise']} ({q['Sets']} x {q['Reps']})")
            
            if st.button("🚀 Start Custom Session", type="primary"):
                st.session_state.workout_queue = st.session_state.builder_queue
                del st.session_state.builder_queue
                st.rerun()


# --- B. COMPACT LOGGING GRID ---
if st.session_state.workout_queue:
    logs_to_save = []
    
    if st.button("Clear Session"): st.session_state.workout_queue = []; st.rerun()
    st.markdown("---")
    
    for i, ex in enumerate(st.session_state.workout_queue):
        cat_color = "red" if "main" in ex.get('Category','').lower() else "blue"
        header = f"**:{cat_color}[{ex['Category']}] {ex['Exercise']}** | *Target: {ex['Guide_Weight']} lbs × {ex['Reps']}*"
        st.markdown(header)
        
        cols = st.columns(ex['Sets'] + 1)
        if cols[0].button("⤵", key=f"cp_{i}", help="Fill all sets"):
            copy_plan_to_actual(i, ex['Sets'])
            st.rerun()

        for s in range(ex['Sets']):
            with cols[s+1]:
                w = st.number_input(f"s{s+1}", value=0.0, step=5.0, key=f"w_{i}_{s}", label_visibility="collapsed", placeholder="Lbs")
                r = st.number_input(f"r{s+1}", value=0, step=1, key=f"r_{i}_{s}", label_visibility="collapsed", placeholder="Reps")
                rpe = st.number_input(f"rpe{s+1}", value=0.0, step=0.5, key=f"rpe_{i}_{s}", label_visibility="collapsed", placeholder="RPE")
                
                logs_to_save.append({
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Program": ex['Meta'].get('Template'),
                    "Week": ex['Meta'].get('Week'),
                    "Day": ex['Meta'].get('Day'),
                    "Category": ex.get('Category', 'Accessory'),
                    "Exercise": ex['Exercise'],
                    "Set": s+1,
                    "Weight": w,
                    "Reps": r,
                    "RPE": rpe
                })
        st.divider()

    if st.button("✅ Finish & Save Log", type="primary", use_container_width=True):
        new_logs = pd.DataFrame(logs_to_save)
        new_logs = new_logs[new_logs['Weight'] > 0]
        if not new_logs.empty:
            updated = pd.concat([conn.read(worksheet="Logs", ttl=0, dtype=str), new_logs], ignore_index=True)
            conn.update(worksheet="Logs", data=updated)
            st.toast("Saved Successfully!", icon="🎉")
            st.session_state.workout_queue = []
            st.rerun()
        else:
            st.warning("Enter some weights first.")
