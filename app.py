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
        div[data-baseweb="tab-list"] { gap: 10px; }
        div[data-baseweb="tab"] {
            height: 50px; width: 100%; justify-content: center; font-weight: bold;
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
                mask = (
                    (df_lib['Template'] == sel_temp) & 
                    (df_lib['Week'] == sel_week) & 
                    (df_lib['Day'] == sel_day)
                )
                rows = df_lib[mask]
                st.session_state.workout_queue = []
                for _, row in rows.iterrows():
                    base_max = get_profile_max(df_profile, row['Exercise'])
                    try: n_sets = int(float(row['Sets']))
                    except: n_sets = 3
                    
                    pct_str = str(row['Pct']) if pd.notna(row['Pct']) else "0"
                    pct_list = parse_multi_value(pct_str, n_sets, is_number=True)
                    rep_str = str(row['Reps']) if pd.notna(row['Reps']) else "5"
                    rep_list = parse_multi_value(rep_str, n_sets, is_number=False)
                    guide_list = []
                    for p in pct_list:
                        gw = int((base_max * p) / 5) * 5 if p > 0 else 0
                        guide_list.append(gw)
                    st.session_state.workout_queue.append({
                        "Category": str(row.get('Category', 'Accessory')),
                        "Exercise": row['Exercise'], "Sets": n_sets,
                        "Rep_List": rep_list, "Guide_List": guide_list,
                        "Meta": {"Template": sel_temp}
                    })
                st.rerun()

# --- ACTIVE SESSION ---
if st.session_state.workout_queue:
    logs_to_save = []
    
    for i, ex in enumerate(st.session_state.workout_queue):
        
        # CARD HEADER
        with st.expander(f"**{ex['Exercise']}**", expanded=True):
            
            # COPY BUTTON
            if st.button("📋 Fill Targets", key=f"cp_{i}", help="Auto-fill"):
                copy_plan_to_actual(i, ex['Sets'])
                st.rerun()
            
            # === 📱 PORTRAIT MODE (TABS) ===
            if "Portrait" in view_mode:
                tab_target, tab_actual = st.tabs(["🎯 Target", "📝 Actual"])
                
                with tab_target:
                    for s in range(ex['Sets']):
                        t_weight = ex['Guide_List'][s] if s < len(ex['Guide_List']) else ex['Guide_List'][-1]
                        t_reps = ex['Rep_List'][s] if s < len(ex['Rep_List']) else ex['Rep_List'][-1]
                        st.info(f"**Set {s+1}:** {t_weight} lbs × {t_reps} reps")

                with tab_actual:
                    # UPDATED: Use ratios [1.5, 1.5, 1.5, 4] to squish inputs to the LEFT
                    col_lbs, col_reps, col_rpe, _ = st.columns([1.5, 1.5, 1.5, 4])
                    col_lbs.markdown("<div class='header-label'>LBS</div>", unsafe_allow_html=True)
                    col_reps.markdown("<div class='header-label'>REPS</div>", unsafe_allow_html=True)
                    col_rpe.markdown("<div class='header-label'>RPE</div>", unsafe_allow_html=True)
                    
                    for s in range(ex['Sets']):
                        # Same squished layout for rows
                        c1, c2, c3, _ = st.columns([1.5, 1.5, 1.5, 4])
                        w = c1.number_input(f"w{s}", value=0.0, step=5.0, key=f"w_{i}_{s}", label_visibility="collapsed")
                        r = c2.number_input(f"r{s}", value=0, step=1, key=f"r_{i}_{s}", label_visibility="collapsed")
                        rpe = c3.number_input(f"rpe{s}", value=0.0, step=0.5, key=f"rpe_{i}_{s}", label_visibility="collapsed")
                        
                        logs_to_save.append({
                            "Date": date.today().strftime("%Y-%m-%d"), "Exercise": ex['Exercise'],
                            "Set": s+1, "Weight": w, "Reps": r, "RPE": rpe
                        })

            # === 💻 LANDSCAPE MODE (SIDE-BY-SIDE) ===
            else:
                c1, c2, c3, c4, c5, c6 = st.columns([1.2, 0.8, 0.5, 1.2, 0.8, 0.8])
                c1.markdown("<div class='header-label'>TARGET</div>", unsafe_allow_html=True)
                c2.markdown("<div class='header-label'>REPS</div>", unsafe_allow_html=True)
                c4.markdown("<div class='header-label'>ACTUAL</div>", unsafe_allow_html=True)
                c5.markdown("<div class='header-label'>REPS</div>", unsafe_allow_html=True)
                c6.markdown("<div class='header-label'>RPE</div>", unsafe_allow_html=True)

                for s in range(ex['Sets']):
                    t_weight = ex['Guide_List'][s] if s < len(ex['Guide_List']) else ex['Guide_List'][-1]
                    t_reps = ex['Rep_List'][s] if s < len(ex['Rep_List']) else ex['Rep_List'][-1]
                    
                    c1, c2, c3, c4, c5, c6 = st.columns([1.2, 0.8, 0.5, 1.2, 0.8, 0.8])
                    c1.markdown(f"<div class='target-box'>{t_weight}</div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='target-box'>{t_reps}</div>", unsafe_allow_html=True)
                    c3.markdown("<div class='arrow-box'>🟩</div>", unsafe_allow_html=True)
                    
                    w = c4.number_input(f"w{s}", value=0.0, step=5.0, key=f"w_{i}_{s}", label_visibility="collapsed")
                    r = c5.number_input(f"r{s}", value=0, step=1, key=f"r_{i}_{s}", label_visibility="collapsed")
                    rpe = c6.number_input(f"rpe{s}", value=0.0, step=0.5, key=f"rpe_{i}_{s}", label_visibility="collapsed")
                    
                    logs_to_save.append({
                        "Date": date.today().strftime("%Y-%m-%d"), "Exercise": ex['Exercise'],
                        "Set": s+1, "Weight": w, "Reps": r, "RPE": rpe
                    })

    st.markdown("---")
    if st.button("✅ Finish & Save", type="primary", use_container_width=True):
        new_logs = pd.DataFrame(logs_to_save)
        new_logs = new_logs.drop_duplicates()
        new_logs = new_logs[new_logs['Weight'] > 0]
        
        if not new_logs.empty:
            try:
                current = conn.read(worksheet="Logs", ttl=0, dtype=str)
                updated = pd.concat([current, new_logs], ignore_index=True)
                conn.update(worksheet="Logs", data=updated)
                st.toast("Saved!", icon="🏆")
                st.session_state.workout_queue = []
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Log at least one set.")
