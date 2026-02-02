import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==========================================
# 1. CONFIG & CSS
# ==========================================
st.set_page_config(page_title="IronOS", page_icon="⚡", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("""
    <style>
        .block-container {padding: 1rem 0.5rem;}
        
        /* Big Inputs for Mobile */
        .stNumberInput input {
            height: 45px; text-align: center; font-weight: bold; font-size: 1.1rem;
            border: 1px solid #ccc; border-radius: 8px;
        }
        
        /* Hide Label Gaps */
        .stNumberInput label {display: none;}
        div[data-baseweb="select"] > div {min-height: 45px;}
        
        /* Target Box Style */
        .target-box {
            background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
            text-align: center; padding: 12px 0; color: #495057; font-weight: bold; font-size: 1rem;
            margin-bottom: 5px;
        }
        
        /* Mobile Tab Styling */
        div[data-baseweb="tab-list"] {
            gap: 10px;
        }
        div[data-baseweb="tab"] {
            height: 50px;
            width: 100%;
            justify-content: center;
            font-weight: bold;
        }
        
        .arrow-box {text-align: center; font-size: 1.5rem; padding-top: 5px;}
        .header-label {font-size: 0.8rem; font-weight: bold; color: #666; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING & PARSING
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
    
    if not df_lib.empty: df_lib.dropna(how='all', inplace=True)
    if not df_profile.empty: df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)

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

def parse_multi_value(value_str, count, is_number=False):
    val_str = str(value_str).replace(" ", "")
    parts = val_str.split(',')
    if len(parts) == 1:
        v = float(parts[0]) if is_number else parts[0]
        return [v] * count
    result = []
    for i in range(count):
        raw = parts[i] if i < len(parts) else parts[-1]
        if is_number:
            try: result.append(float(raw))
            except: result.append(0.0)
        else: result.append(raw)
    return result

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.write("### 📱 Display Settings")
    # THE MAGIC TOGGLE
    view_mode = st.radio("Orientation", ["Portrait (Mobile)", "Landscape (Wide)"], index=0)
    
    st.markdown("---")
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()

df_lib, df_profile, df_dir, RPE_DATA = load_static_data()

# ==========================================
# 3. SESSION LOGIC
# ==========================================
if 'workout_queue' not in st.session_state: st.session_state.workout_queue = []

def copy_plan_to_actual(index, sets):
    ex = st.session_state.workout_queue[index]
    guides = ex.get('Guide_List', [0]*sets)
    reps = ex.get('Rep_List', ['5']*sets)
    for s in range(sets):
        st.session_state[f"w_{index}_{s}"] = float(guides[s])
        try: st.session_state[f"r_{index}_{s}"] = int(str(reps[s]).replace("+", "").strip())
        except: st.session_state[f"r_{index}_{s}"] = 5

# ==========================================
# 4. APP INTERFACE
# ==========================================
c_h1, c_h2 = st.columns([3, 1])
c_h1.markdown(f"### 📅 {date.today().strftime('%A, %b %d')}")
if c_h2.button("Reset", use_container_width=True):
    st.session_state.workout_queue = []
    st.rerun()

st.markdown("---")

# --- BUILDER (HIDDEN IF ACTIVE) ---
if not st.session_state.workout_queue:
    templates = sorted(list(df_lib['Template'].unique())) if not df_lib.empty else []
    if "Custom Build" not in templates: templates.insert(0, "Custom Build")
    
    sel_temp = st.selectbox("Select Mission", templates, index=None, placeholder="Choose Program...")

    if sel_temp == "Custom Build":
        l1 = df_profile['Lift'].unique().tolist() if not df_profile.empty else []
        l2 = df_lib['Exercise'].unique().tolist() if not df_lib.empty else []
        l3 = df_dir['Exercise'].unique().tolist() if not df_dir.empty else []
        all_ex = sorted(list(set(l1 + l2 + l3)))
        
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        new_ex = c1.selectbox("Lift", all_ex, index=None)
        new_sets = c2.number_input("Sets", 1, 10, 3)
        new_reps = c3.text_input("Reps", "5")
        if c4.button("Add +", type="primary", use_container_width=True):
            if new_ex:
                if 'builder_queue' not in st.session_state: st.session_state.builder_queue = []
                st.session_state.builder_queue.append({
                    "Category": "Custom", "Exercise": new_ex, "Sets": int(new_sets), "Reps": new_reps,
                    "Guide_List": [0] * int(new_sets), "Rep_List": [new_reps] * int(new_sets),
                    "Meta": {"Template": "Custom"}
                })
                st.rerun()
        if 'builder_queue' in st.session_state and st.session_state.builder_queue:
            st.caption("Queue:")
            for q in st.session_state.builder_queue: st.text(f"• {q['Exercise']}")
            if st.button("🚀 Start", type="primary", use_container_width=True):
                st.session_state.workout_queue = st.session_state.builder_queue
                del st.session_state.builder_queue
                st.rerun()

    elif sel_temp:
        weeks = sorted(df_lib[df_lib['Template'] == sel_temp]['Week'].unique())
        sel_week = st.selectbox("Week", weeks, index=None)
        if sel_week:
            days = sorted(df_lib[(df_lib['Template'] == sel_temp) & (df_lib['Week'] == sel_week)]['Day'].unique())
            sel_day = st.selectbox("Day", days, index=None)
            if sel_day and st.button("🚀 Load", type="primary", use_container_width=True):
                rows = df_lib[(df_lib['Template'] == sel_temp) & (df_lib['Week']
