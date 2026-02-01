import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
# ==========================================
# 1. CONFIG & CACHING
# ==========================================
st.set_page_config(page_title="IronOS Command", page_icon="⚡", layout="centered")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_rpe_table():
    try:
        # Force string read to prevent type errors, then convert
        df = conn.read(worksheet="Constants", ttl=0, dtype=str)
        rpe_dict = {}
        for _, row in df.iterrows():
            # Clean up the RPE row value
            rpe_val_str = str(row['RPE']).strip()
            if not rpe_val_str or rpe_val_str.lower() == 'nan': continue
            
            rpe_val = float(rpe_val_str)
            rpe_dict[rpe_val] = {}
            
            for c in df.columns:
                if c != 'RPE':
                    # Only try to read columns that look like integers (1, 2, 3...)
                    if str(c).isdigit():
                        val_str = str(row[c]).strip()
                        if val_str and val_str.lower() != 'nan':
                             rpe_dict[rpe_val][int(c)] = float(val_str)
        return rpe_dict
    except Exception as e:
        # Fallback if table is empty or broken
        return {10: {1: 1.0}} 

def get_profile_max(df_profile, lift_name):
    if df_profile.empty: return 0.0
    lift_name = lift_name.lower()
    for _, row in df_profile.iterrows():
        # Safe read of Lift and Max
        p_lift = str(row.get('Lift', '')).lower()
        p_max = row.get('Max', 0)
        
        if p_lift in lift_name:
            try: return float(p_max)
            except: return 0.0
    return 0.0

def calc_load_from_max(one_rm, reps, rpe, rpe_table):
    if one_rm == 0: return 0
    avail_rpes = sorted(rpe_table.keys())
    if not avail_rpes: return 0
    
    closest_rpe = min(avail_rpes, key=lambda x: abs(x - rpe))
    avail_reps = sorted(rpe_table[closest_rpe].keys())
    if not avail_reps: return 0
    
    closest_rep = min(avail_reps, key=lambda x: abs(x - reps))
    pct = rpe_table[closest_rpe][closest_rep]
    return int((one_rm * pct) / 5) * 5

# ==========================================
# 2. LOAD DATA (SAFE MODE)
# ==========================================
try:
    # ttl=0 -> Force fresh data
    # dtype=str -> Read EVERYTHING as text first to stop 400 Errors
    df_lib = conn.read(worksheet="Master", ttl=0, dtype=str)
    df_logs = conn.read(worksheet="Logs", ttl=0, dtype=str)
    df_profile = conn.read(worksheet="Profile", ttl=0, dtype=str)
    
    RPE_DATA = load_rpe_table()

    # --- CLEANUP: Convert Text back to Numbers safely ---
    if not df_lib.empty:
        # Drop completely empty rows that might be causing "ghost" issues
        df_lib.dropna(how='all', inplace=True)
        
        # Safe conversions
        df_lib['Sets'] = pd.to_numeric(df_lib['Sets'], errors='coerce').fillna(0).astype(int)
        df_lib['Pct'] = pd.to_numeric(df_lib['Pct'], errors='coerce').fillna(0.0)
        
    if not df_profile.empty:
        df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)

except Exception as e:
    st.error(f"Data Load Error: {e}")
    st.stop()

# ==========================================
# 3. HELPER: SESSION MANAGEMENT
# ==========================================
if 'workout_queue' not in st.session_state:
    st.session_state.workout_queue = []

def move_exercise(index, direction):
    queue = st.session_state.workout_queue
    if direction == "up" and index > 0:
        queue[index], queue[index-1] = queue[index-1], queue[index]
    elif direction == "down" and index < len(queue) - 1:
        queue[index], queue[index+1] = queue[index+1], queue[index]

def copy_plan_to_actual(index, sets):
    ex = st.session_state.workout_queue[index]
    guide = ex.get('Guide_Weight', 0)
    for s in range(sets):
        st.session_state[f"w_{index}_{s}"] = float(guide)
        try: 
            # Remove any "+" signs if they exist before converting
            clean_reps = str(ex['Reps']).replace("+", "").strip()
            st.session_state[f"r_{index}_{s}"] = int(clean_reps)
        except: 
            st.session_state[f"r_{index}_{s}"] = 5

# ==========================================
# 4. APP INTERFACE
# ==========================================
st.title("⚡ IronOS Command")

# --- A. SESSION LOADER ---
if not st.session_state.workout_queue:
    with st.expander("📂 Mission Select", expanded=True):
        if not df_lib.empty:
            templates = df_lib['Template'].unique()
            sel_temp = st.selectbox("Template", templates)
            
            if sel_temp:
                weeks = sorted(df_lib[df_lib['Template'] == sel_temp]['Week'].unique())
                c1, c2 = st.columns(2)
                sel_week = c1.selectbox("Week", weeks)
                days = sorted(df_lib[(df_lib['Template'] == sel_temp) & (df_lib['Week'] == sel_week)]['Day'].unique())
                sel_day = c2.selectbox("Day", days)
                
                if st.button("🚀 Load Mission", type="primary", use_container_width=True):
                    rows = df_lib[
                        (df_lib['Template'] == sel_temp) & 
                        (df_lib['Week'] == sel_week) & 
                        (df_lib['Day'] == sel_day)
                    ]
                    st.session_state.workout_queue = []
                    for _, row in rows.iterrows():
                        base_max = get_profile_max(df_profile, row['Exercise'])
                        pct = float(row['Pct'])
                        guide = int((base_max * pct) / 5) * 5 if pct > 0 else 0
                        
                        cat = str(row['Category']) if pd.notna(row['Category']) else "Accessory"
                        
                        st.session_state.workout_queue.append({
                            "Category": cat,
                            "Exercise": row['Exercise'],
                            "Modifiers": str(row['Modifiers']) if pd.notna(row['Modifiers']) else "",
                            "Sets": int(row['Sets']),
                            "Reps": str(row['Reps']),
                            "RPE_Target": str(row['RPE']) if pd.notna(row['RPE']) else "",
                            "Guide_Weight": guide,
                            "Base_Max": base_max,
                            "Note": str(row['Notes']) if pd.notna(row['Notes']) else "",
                            "Meta": {"Template": sel_temp, "Week": sel_week, "Day": sel_day}
                        })
                    st.rerun()
        else:
            st.warning("Library is empty. Please add data to 'Master' tab.")

# --- B. ACTIVE SESSION ---
if st.session_state.workout_queue:
    
    if st.button("Cancel / Clear Session"):
        st.session_state.workout_queue = []
        st.rerun()

    logs_to_save = []
    
    for i, ex in enumerate(st.session_state.workout_queue):
        
        # CARD HEADER
        cat = ex['Category'].lower()
        if "main" in cat: badge = "🔴" 
        elif "supp" in cat: badge = "🔵"
        else: badge = "⚪"
        
        header_text = f"{badge} {ex['Exercise']} {f'({ex['Modifiers']})' if ex['Modifiers'] else ''}"
        
        with st.expander(header_text, expanded=True):
            
            c_tools = st.columns([1, 1, 4])
            if c_tools[0].button("⬆", key=f"up_{i}"): move_exercise(i, "up"); st.rerun()
            if c_tools[1].button("⬇", key=f"down_{i}"): move_exercise(i, "down"); st.rerun()
            
            tab_plan, tab_act = st.tabs(["🎯 Plan & Calc", "📝 Actual Log"])
            
            with tab_plan:
                c1, c2 = st.columns(2)
                c1.markdown(f"**Category:** {ex['Category']}")
                c1.markdown(f"**Target:** {ex['Guide_Weight']} lbs")
                c1.markdown(f"**RPE:** {ex['RPE_Target']}")
                c2.info(f"📝 {ex['Note']}")
                
                st.divider()
                st.caption("🧮 Quick Load Calculator")
                lc1, lc2, lc3 = st.columns(3)
                calc_reps = lc1.number_input("Reps", value=5, key=f"cr_{i}")
                calc_rpe = lc2.number_input("RPE", value=8.0, step=0.5, key=f"crpe_{i}")
                
                calc_load = calc_load_from_max(ex['Base_Max'], calc_reps, calc_rpe, RPE_DATA)
                lc3.metric("Load", f"{calc_load} lbs")
                
                if st.button(f"⤵️ Copy {ex['Guide_Weight']}lbs to Actual", key=f"copy_{i}"):
                    copy_plan_to_actual(i, ex['Sets'])
                    st.rerun()

            with tab_act:
                new_mod = st.text_input("Modifiers", value=ex['Modifiers'], key=f"mod_{i}")
                h1, h2, h3 = st.columns([1.5, 1, 1])
                h1.caption("Lbs"); h2.caption("Reps"); h3.caption("RPE")
                
                for s in range(ex['Sets']):
                    r1, r2, r3 = st.columns([1.5, 1, 1])
                    w = r1.number_input(f"s{s}w", step=5.0, key=f"w_{i}_{s}", label_visibility="collapsed")
                    r = r2.number_input(f"s{s}r", step=1, key=f"r_{i}_{s}", label_visibility="collapsed")
                    rpe = r3.number_input(f"s{s}rpe", step=0.5, key=f"rpe_{i}_{s}", label_visibility="collapsed")
                    
                    logs_to_save.append({
                        "Date": date.today().strftime("%Y-%m-%d"),
                        "Program": ex['Meta'].get('Template'),
                        "Week": ex['Meta'].get('Week'),
                        "Day": ex['Meta'].get('Day'),
                        "Category": ex['Category'],
                        "Exercise": ex['Exercise'],
                        "Modifiers": new_mod,
                        "Set": s+1,
                        "Weight": w,
                        "Reps": r,
                        "RPE": rpe
                    })

    st.divider()
    if st.button("✅ Finish & Save", type="primary", use_container_width=True):
        new_logs = pd.DataFrame(logs_to_save)
        new_logs = new_logs[new_logs['Weight'] > 0]
        if not new_logs.empty:
            updated = pd.concat([conn.read(worksheet="Logs", ttl=0), new_logs], ignore_index=True)
            conn.update(worksheet="Logs", data=updated)
            st.balloons()
            st.success("Session Saved!")
            st.session_state.workout_queue = []
            st.rerun()
        else:
            st.warning("No data logged.")
