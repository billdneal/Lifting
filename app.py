import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==========================================
# 1. CONFIG & CSS (OPTIMIZED FOR MOBILE)
# ==========================================
st.set_page_config(page_title="IronOS", page_icon="⚡", layout="wide")

# Initialize connection - wrap in try/except
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Connection Error: {e}")
    # Create a dummy connection object to prevent further errors
    class DummyConnection:
        def read(self, **kwargs):
            return pd.DataFrame()
        def update(self, **kwargs):
            pass
    conn = DummyConnection()

st.markdown("""
    <style>
        /* 1. HIDE +/- BUTTONS AND WARNINGS */
        div[data-testid="stNumberInput"] button { display: none !important; }
        .stNumberInput input { width: 100% !important; }
        
        /* 2. COMPACT CONTAINER */
        .main .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
        
        /* 3. CUSTOM NUMBER INPUT STYLE */
        .compact-input {
            height: 45px !important;
            min-height: 45px !important;
            text-align: center !important;
            font-weight: bold !important;
            font-size: 1rem !important;
            border: 1px solid #555 !important;
            border-radius: 6px !important;
            background-color: #0e1117 !important;
            padding: 0 2px !important;
        }
        
        .compact-input:focus {
            border-color: #ff4b4b !important;
            box-shadow: 0 0 0 1px #ff4b4b !important;
        }
        
        /* 4. TARGET BOX STYLES */
        .target-box {
            background: linear-gradient(135deg, #2d3436, #636e72);
            border: 1px solid #444;
            border-radius: 6px;
            text-align: center;
            padding: 10px 5px;
            color: white;
            font-weight: bold;
            font-size: 1.1rem;
            height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }
        
        .target-reps {
            background: linear-gradient(135deg, #1a5276, #3498db);
        }
        
        /* 5. COMPACT HEADERS */
        .compact-header {
            font-size: 0.7rem !important;
            font-weight: bold !important;
            color: #aaa !important;
            text-align: center !important;
            margin-bottom: 2px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }
        
        /* 6. SET NUMBER */
        .set-number {
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9rem;
            color: #aaa;
            height: 45px;
        }
        
        /* 7. REMOVE ALL LABELS */
        div[data-testid="stNumberInput"] > label,
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stTextInput"] > label {
            display: none !important;
        }
        
        /* 8. BUTTON STYLES */
        div[data-testid="stButton"] button {
            height: 45px !important;
            min-height: 45px !important;
            padding: 0 8px !important;
        }
        
        /* 9. EXPANDER STYLES */
        .stExpander {
            border: 1px solid #333 !important;
            border-radius: 8px !important;
            margin: 5px 0 !important;
        }
        
        .stExpander summary {
            padding: 0.5rem 1rem !important;
        }
        
        /* 10. FORCE NO GAPS BETWEEN COLUMNS */
        [data-testid="column"] {
            padding: 0 2px !important;
            min-width: 0 !important;
            gap: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING (WITH BETTER ERROR HANDLING)
# ==========================================
@st.cache_data(ttl=600)
def load_static_data():
    # Initialize with empty DataFrames
    df_lib = pd.DataFrame()
    df_profile = pd.DataFrame()
    df_dir = pd.DataFrame()
    rpe_dict = {10: {1: 1.0}}
    
    try:
        df_lib = conn.read(worksheet="Master", ttl=0, dtype=str)
    except Exception as e:
        st.sidebar.warning(f"Could not load Master: {str(e)[:50]}")
    
    try:
        df_profile = conn.read(worksheet="Profile", ttl=0, dtype=str)
    except Exception as e:
        st.sidebar.warning(f"Could not load Profile: {str(e)[:50]}")
    
    try:
        df_dir = conn.read(worksheet="Directory", ttl=0, dtype=str)
    except Exception as e:
        st.sidebar.warning(f"Could not load Directory: {str(e)[:50]}")
    
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
                except:
                    continue
    except Exception as e:
        st.sidebar.warning(f"Could not load Constants: {str(e)[:50]}")
    
    # Clean up data
    if not df_lib.empty:
        df_lib.dropna(how='all', inplace=True)
    else:
        # Create empty DataFrame with expected columns
        df_lib = pd.DataFrame(columns=['Template', 'Week', 'Day', 'Exercise', 'Sets', 'Reps', 'Pct', 'Category'])
    
    if not df_profile.empty:
        df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)
    else:
        df_profile = pd.DataFrame(columns=['Lift', 'Max'])
    
    if df_dir.empty:
        df_dir = pd.DataFrame(columns=['Exercise'])

    return df_lib, df_profile, df_dir, rpe_dict

def get_profile_max(df_profile, lift_name):
    if df_profile.empty: 
        return 0.0
    lift_name = lift_name.lower()
    for _, row in df_profile.iterrows():
        p_lift = str(row.get('Lift', '')).lower()
        if p_lift in lift_name:
            try: 
                return float(row.get('Max', 0))
            except: 
                return 0.0
    return 0.0

def parse_multi_value(value_str, count, is_number=False):
    """Parse comma-separated values, handling None and empty values"""
    # Handle None, NaN, or empty values
    if value_str is None or pd.isna(value_str):
        value_str = ""
    
    # Convert to string and clean
    val_str = str(value_str).replace(" ", "").strip()
    
    # If empty after cleaning, return default values
    if not val_str:
        if is_number:
            return [0.0] * count
        else:
            return ["5"] * count
    
    parts = val_str.split(',')
    if len(parts) == 1:
        try:
            v = float(parts[0]) if is_number else parts[0]
            return [v] * count
        except (ValueError, TypeError):
            if is_number:
                return [0.0] * count
            else:
                return ["5"] * count
    
    result = []
    for i in range(count):
        raw = parts[i] if i < len(parts) else parts[-1]
        if is_number:
            try: 
                result.append(float(raw))
            except (ValueError, TypeError): 
                result.append(0.0)
        else: 
            result.append(str(raw))
    return result

# Load data with error handling
try:
    df_lib, df_profile, df_dir, RPE_DATA = load_static_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    # Initialize with empty dataframes
    df_lib = pd.DataFrame(columns=['Template', 'Week', 'Day', 'Exercise', 'Sets', 'Reps', 'Pct', 'Category'])
    df_profile = pd.DataFrame(columns=['Lift', 'Max'])
    df_dir = pd.DataFrame(columns=['Exercise'])
    RPE_DATA = {10: {1: 1.0}}

# ==========================================
# 3. SESSION LOGIC
# ==========================================
if 'workout_queue' not in st.session_state: 
    st.session_state.workout_queue = []

def copy_plan_to_actual(index, sets):
    ex = st.session_state.workout_queue[index]
    guides = ex.get('Guide_List', [0]*sets)
    reps = ex.get('Rep_List', ['5']*sets)
    for s in range(sets):
        st.session_state[f"w_{index}_{s}"] = float(guides[s])
        try: 
            st.session_state[f"r_{index}_{s}"] = int(str(reps[s]).replace("+", "").strip())
        except: 
            st.session_state[f"r_{index}_{s}"] = 5
        st.session_state[f"rpe_{index}_{s}"] = 0.0

# ==========================================
# 4. APP INTERFACE
# ==========================================
c_h1, c_h2 = st.columns([3, 1])
c_h1.markdown(f"### {date.today().strftime('%A, %b %d')}")
if c_h2.button("Reset", use_container_width=True):
    st.session_state.workout_queue = []
    st.rerun()

st.markdown("---")

# --- BUILDER (HIDDEN IF ACTIVE) ---
if not st.session_state.workout_queue:
    # FIXED: Handle empty or non-existent 'Template' column
    if not df_lib.empty and 'Template' in df_lib.columns:
        templates = sorted(list(df_lib['Template'].unique())) 
    else:
        templates = []
    
    if "Custom Build" not in templates: 
        templates.insert(0, "Custom Build")
    
    sel_temp = st.selectbox("Select Mission", templates, index=None, placeholder="Choose Program...")

    if sel_temp == "Custom Build":
        # Collect all possible exercises safely
        all_ex = []
        if not df_profile.empty and 'Lift' in df_profile.columns:
            all_ex.extend(df_profile['Lift'].unique().tolist())
        if not df_lib.empty and 'Exercise' in df_lib.columns:
            all_ex.extend(df_lib['Exercise'].unique().tolist())
        if not df_dir.empty and 'Exercise' in df_dir.columns:
            all_ex.extend(df_dir['Exercise'].unique().tolist())
        
        all_ex = sorted(list(set([str(ex) for ex in all_ex if pd.notna(ex)])))
        
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        new_ex = c1.selectbox("Lift", all_ex, index=None)
        new_sets = c2.number_input("Sets", 1, 10, 3)
        new_reps = c3.text_input("Reps", "5")
        if c4.button("Add +", type="primary", use_container_width=True):
            if new_ex:
                if 'builder_queue' not in st.session_state: 
                    st.session_state.builder_queue = []
                st.session_state.builder_queue.append({
                    "Category": "Custom", 
                    "Exercise": new_ex, 
                    "Sets": int(new_sets), 
                    "Reps": new_reps,
                    "Guide_List": [0] * int(new_sets), 
                    "Rep_List": [new_reps] * int(new_sets),
                    "Meta": {"Template": "Custom"}
                })
                st.rerun()
        
        if 'builder_queue' in st.session_state and st.session_state.builder_queue:
            st.caption("Queue:")
            for q in st.session_state.builder_queue: 
                st.text(f"• {q['Exercise']}")
            if st.button("🚀 Start", type="primary", use_container_width=True):
                st.session_state.workout_queue = st.session_state.builder_queue
                del st.session_state.builder_queue
                st.rerun()

    elif sel_temp:
        # Check if required columns exist
        required_cols = ['Template', 'Week', 'Day', 'Exercise']
        if all(col in df_lib.columns for col in required_cols):
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
                        try: 
                            n_sets = int(float(row['Sets']))
                        except: 
                            n_sets = 3
                        
                        # SAFE: Handle potential None/NaN values
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
                            "Exercise": row['Exercise'], 
                            "Sets": n_sets,
                            "Rep_List": rep_list, 
                            "Guide_List": guide_list,
                            "Meta": {"Template": sel_temp}
                        })
                    st.rerun()
        else:
            st.warning("Required columns missing from Master sheet. Please check your Google Sheet.")

# --- ACTIVE SESSION ---
if st.session_state.workout_queue:
    logs_to_save = []
    
    for i, ex in enumerate(st.session_state.workout_queue):
        
        with st.expander(f"**{ex['Exercise']}** • {ex['Sets']} sets", expanded=True):
            # Header with category and fill button
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"*{ex['Category']}*")
            if col2.button("📋 Fill", key=f"cp_{i}", use_container_width=True, help="Auto-fill targets"):
                copy_plan_to_actual(i, ex['Sets'])
                st.rerun()
            
            # SIMPLIFIED VIEW - ALWAYS SHOW SINGLE ROW LAYOUT
            # Remove the view_mode toggle for now to simplify
            
            # Single row header
            st.markdown("""
            <div style="display: flex; width: 100%; margin-bottom: 5px;">
                <div style="width: 12%; text-align: center; font-size: 0.7rem; color: #aaa; font-weight: bold;">SET</div>
                <div style="width: 22%; text-align: center; font-size: 0.7rem; color: #aaa; font-weight: bold;">TARGET</div>
                <div style="width: 22%; text-align: center; font-size: 0.7rem; color: #aaa; font-weight: bold;">REPS</div>
                <div style="width: 22%; text-align: center; font-size: 0.7rem; color: #aaa; font-weight: bold;">ACTUAL</div>
                <div style="width: 11%; text-align: center; font-size: 0.7rem; color: #aaa; font-weight: bold;">REPS</div>
                <div style="width: 11%; text-align: center; font-size: 0.7rem; color: #aaa; font-weight: bold;">RPE</div>
            </div>
            """, unsafe_allow_html=True)
            
            for s in range(ex['Sets']):
                # Get target values - with safe defaults
                t_weight = ex['Guide_List'][s] if s < len(ex['Guide_List']) else ex['Guide_List'][-1] if ex['Guide_List'] else 0
                t_reps = ex['Rep_List'][s] if s < len(ex['Rep_List']) else ex['Rep_List'][-1] if ex['Rep_List'] else "5"
                
                # Create columns WITHOUT gaps
                cols = st.columns([0.12, 0.22, 0.22, 0.22, 0.11, 0.11], gap="small")
                
                # Set number
                cols[0].markdown(f"<div class='set-number'>{s+1}</div>", unsafe_allow_html=True)
                
                # Target weight
                cols[1].markdown(f"<div class='target-box'>{int(t_weight)}</div>", unsafe_allow_html=True)
                
                # Target reps
                cols[2].markdown(f"<div class='target-box target-reps'>{t_reps}</div>", unsafe_allow_html=True)
                
                # Actual weight
                with cols[3]:
                    w_key = f"w_{i}_{s}"
                    if w_key not in st.session_state:
                        st.session_state[w_key] = 0.0
                    w = st.number_input(
                        f"w_{i}_{s}",
                        value=st.session_state[w_key],
                        step=5.0,
                        key=w_key,
                        label_visibility="collapsed",
                        min_value=0.0,
                        max_value=1000.0,
                        format="%d"
                    )
                
                # Actual reps
                with cols[4]:
                    r_key = f"r_{i}_{s}"
                    if r_key not in st.session_state:
                        st.session_state[r_key] = 0
                    r = st.number_input(
                        f"r_{i}_{s}",
                        value=st.session_state[r_key],
                        step=1,
                        key=r_key,
                        label_visibility="collapsed",
                        min_value=0,
                        max_value=100,
                        format="%d"
                    )
                
                # RPE
                with cols[5]:
                    rpe_key = f"rpe_{i}_{s}"
                    if rpe_key not in st.session_state:
                        st.session_state[rpe_key] = 0.0
                    rpe = st.number_input(
                        f"rpe_{i}_{s}",
                        value=st.session_state[rpe_key],
                        step=0.5,
                        key=rpe_key,
                        label_visibility="collapsed",
                        min_value=0.0,
                        max_value=10.0,
                        format="%.1f"
                    )
                
                logs_to_save.append({
                    "Date": date.today().strftime("%Y-%m-%d"), 
                    "Exercise": ex['Exercise'],
                    "Set": s+1, 
                    "Weight": w, 
                    "Reps": r, 
                    "RPE": rpe
                })
                
                # Add subtle separator between sets
                if s < ex['Sets'] - 1:
                    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

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
            except Exception as e: 
                st.error(f"Error saving: {e}")
        else: 
            st.warning("Log at least one set.")