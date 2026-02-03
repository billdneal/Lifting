import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ==========================================
# 1. CONFIG & CSS
# ==========================================
st.set_page_config(page_title="IronOS", page_icon="⚡", layout="wide")

# Initialize connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Connection Error: {e}")
    class DummyConnection:
        def read(self, **kwargs): return pd.DataFrame()
        def update(self, **kwargs): pass
    conn = DummyConnection()

# CSS to force horizontal layout
st.markdown("""
    <style>
    /* Force horizontal layout and remove stacking */
    .horizontal-layout {
        display: flex !important;
        flex-direction: row !important;
        width: 100% !important;
        gap: 2px !important;
        margin-bottom: 5px !important;
    }
    
    .horizontal-cell {
        flex: 1 !important;
        min-width: 0 !important;
        text-align: center !important;
    }
    
    /* Hide number input buttons and labels */
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    
    div[data-testid="stNumberInput"] > label {
        display: none !important;
    }
    
    /* Compact number inputs */
    .stNumberInput input {
        height: 45px !important;
        text-align: center !important;
        font-weight: bold !important;
        font-size: 1rem !important;
        padding: 0 5px !important;
        margin: 0 !important;
        width: 100% !important;
    }
    
    /* Target display boxes */
    .target-box {
        background: linear-gradient(135deg, #2d3436, #636e72);
        border: 1px solid #444;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        font-size: 1rem;
        height: 45px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 5px;
        margin: 0;
    }
    
    .reps-box {
        background: linear-gradient(135deg, #1a5276, #3498db);
    }
    
    /* Set number */
    .set-number {
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.9rem;
        color: #aaa;
        height: 45px;
    }
    
    /* Header labels */
    .header-label {
        font-size: 0.7rem;
        font-weight: bold;
        color: #aaa;
        text-align: center;
        margin-bottom: 2px;
        text-transform: uppercase;
    }
    
    /* Make everything compact */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* Adjust for mobile */
    @media (max-width: 768px) {
        .horizontal-layout {
            gap: 1px !important;
        }
        .stNumberInput input {
            font-size: 0.9rem !important;
        }
        .target-box {
            font-size: 0.9rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING
# ==========================================
@st.cache_data(ttl=600)
def load_static_data():
    df_lib = pd.DataFrame()
    df_profile = pd.DataFrame()
    df_dir = pd.DataFrame()
    
    try:
        df_lib = conn.read(worksheet="Master", ttl=0, dtype=str)
    except:
        pass
    
    try:
        df_profile = conn.read(worksheet="Profile", ttl=0, dtype=str)
    except:
        pass
    
    try:
        df_dir = conn.read(worksheet="Directory", ttl=0, dtype=str)
    except:
        pass
    
    # Ensure DataFrames have expected columns
    if df_lib.empty:
        df_lib = pd.DataFrame(columns=['Template', 'Week', 'Day', 'Exercise', 'Sets', 'Reps', 'Pct', 'Category'])
    else:
        df_lib.dropna(how='all', inplace=True)
    
    if df_profile.empty:
        df_profile = pd.DataFrame(columns=['Lift', 'Max'])
    else:
        df_profile['Max'] = pd.to_numeric(df_profile['Max'], errors='coerce').fillna(0.0)
    
    if df_dir.empty:
        df_dir = pd.DataFrame(columns=['Exercise'])
    
    return df_lib, df_profile, df_dir

def get_profile_max(df_profile, lift_name):
    if df_profile.empty:
        return 0.0
    lift_name = str(lift_name).lower()
    for _, row in df_profile.iterrows():
        p_lift = str(row.get('Lift', '')).lower()
        if p_lift in lift_name:
            try:
                return float(row.get('Max', 0))
            except:
                return 0.0
    return 0.0

def parse_multi_value(value_str, count, is_number=False):
    """Parse comma-separated values"""
    if pd.isna(value_str) or value_str is None:
        value_str = ""
    val_str = str(value_str).replace(" ", "").strip()
    
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
        except:
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
            except:
                result.append(0.0)
        else:
            result.append(str(raw))
    return result

# Load data
df_lib, df_profile, df_dir = load_static_data()

# ==========================================
# 3. SESSION STATE
# ==========================================
if 'workout_queue' not in st.session_state:
    st.session_state.workout_queue = []
if 'builder_queue' not in st.session_state:
    st.session_state.builder_queue = []

def copy_plan_to_actual(index, sets):
    """Copy target values to actual inputs"""
    ex = st.session_state.workout_queue[index]
    guides = ex.get('Guide_List', [0] * sets)
    reps = ex.get('Rep_List', ['5'] * sets)
    
    for s in range(sets):
        # Get the target values for this set
        target_weight = guides[s] if s < len(guides) else guides[-1] if guides else 0
        target_reps = reps[s] if s < len(reps) else reps[-1] if reps else '5'
        
        # Convert target_reps to integer
        try:
            reps_int = int(str(target_reps).replace('+', '').strip())
        except:
            reps_int = 5
        
        # Set session state values
        st.session_state[f"w_{index}_{s}"] = float(target_weight)
        st.session_state[f"r_{index}_{s}"] = reps_int
        st.session_state[f"rpe_{index}_{s}"] = 0.0

# ==========================================
# 4. MAIN APP
# ==========================================
st.title("⚡ IronOS")
st.markdown(f"**{date.today().strftime('%A, %b %d')}**")

if st.button("Reset Session", type="secondary"):
    st.session_state.workout_queue = []
    st.session_state.builder_queue = []
    st.rerun()

st.markdown("---")

# ==========================================
# 5. WORKOUT BUILDER (when no active workout)
# ==========================================
if not st.session_state.workout_queue:
    st.markdown("### 📋 Select or Build Workout")
    
    # Get available templates
    if not df_lib.empty and 'Template' in df_lib.columns:
        templates = sorted(df_lib['Template'].dropna().unique().tolist())
    else:
        templates = []
    
    # Add Custom Build option
    all_templates = ["Custom Build"] + templates
    
    selected_template = st.selectbox(
        "Choose Program",
        all_templates,
        index=None,
        placeholder="Select a program or create custom..."
    )
    
    # CUSTOM BUILDER
    if selected_template == "Custom Build":
        st.markdown("#### 🛠️ Custom Workout Builder")
        
        # Get all available exercises
        all_exercises = []
        if not df_profile.empty and 'Lift' in df_profile.columns:
            all_exercises.extend(df_profile['Lift'].dropna().unique().tolist())
        if not df_lib.empty and 'Exercise' in df_lib.columns:
            all_exercises.extend(df_lib['Exercise'].dropna().unique().tolist())
        if not df_dir.empty and 'Exercise' in df_dir.columns:
            all_exercises.extend(df_dir['Exercise'].dropna().unique().tolist())
        
        all_exercises = sorted(list(set([str(ex) for ex in all_exercises if pd.notna(ex)])))
        
        # Builder interface
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            new_exercise = st.selectbox("Exercise", all_exercises, index=None, key="builder_exercise")
        with col2:
            new_sets = st.number_input("Sets", 1, 10, 3, key="builder_sets")
        with col3:
            new_reps = st.text_input("Reps", "5", key="builder_reps")
        with col4:
            if st.button("➕ Add", use_container_width=True, type="primary"):
                if new_exercise:
                    # Calculate guide weight from profile max
                    base_max = get_profile_max(df_profile, new_exercise)
                    guide_list = [base_max] * new_sets if base_max > 0 else [0] * new_sets
                    
                    # Parse reps
                    rep_list = parse_multi_value(new_reps, new_sets, is_number=False)
                    
                    st.session_state.builder_queue.append({
                        "Category": "Custom",
                        "Exercise": new_exercise,
                        "Sets": int(new_sets),
                        "Rep_List": rep_list,
                        "Guide_List": guide_list,
                        "Meta": {"Template": "Custom"}
                    })
                    st.rerun()
        
        # Show builder queue
        if st.session_state.builder_queue:
            st.markdown("#### 📝 Current Workout")
            for i, item in enumerate(st.session_state.builder_queue):
                st.markdown(f"**{i+1}. {item['Exercise']}** - {item['Sets']} sets")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Clear Queue", type="secondary"):
                    st.session_state.builder_queue = []
                    st.rerun()
            with col2:
                if st.button("🚀 Start Workout", type="primary"):
                    st.session_state.workout_queue = st.session_state.builder_queue.copy()
                    st.session_state.builder_queue = []
                    st.rerun()
    
    # PRE-DEFINED TEMPLATE
    elif selected_template:
        st.markdown(f"#### 📁 {selected_template}")
        
        # Get weeks for this template
        weeks = sorted(df_lib[df_lib['Template'] == selected_template]['Week'].dropna().unique())
        selected_week = st.selectbox("Week", weeks, index=None)
        
        if selected_week:
            # Get days for this week
            days = sorted(df_lib[(df_lib['Template'] == selected_template) & 
                                (df_lib['Week'] == selected_week)]['Day'].dropna().unique())
            selected_day = st.selectbox("Day", days, index=None)
            
            if selected_day and st.button("🚀 Load Workout", type="primary"):
                # Filter exercises for this template/week/day
                workout_data = df_lib[(df_lib['Template'] == selected_template) &
                                     (df_lib['Week'] == selected_week) &
                                     (df_lib['Day'] == selected_day)]
                
                st.session_state.workout_queue = []
                for _, row in workout_data.iterrows():
                    base_max = get_profile_max(df_profile, row['Exercise'])
                    
                    try:
                        n_sets = int(float(row['Sets']))
                    except:
                        n_sets = 3
                    
                    # Parse percentages
                    pct_str = str(row['Pct']) if pd.notna(row['Pct']) else "0"
                    pct_list = parse_multi_value(pct_str, n_sets, is_number=True)
                    
                    # Parse reps
                    rep_str = str(row['Reps']) if pd.notna(row['Reps']) else "5"
                    rep_list = parse_multi_value(rep_str, n_sets, is_number=False)
                    
                    # Calculate guide weights
                    guide_list = []
                    for p in pct_list:
                        guide_weight = int((base_max * p) / 5) * 5 if p > 0 else 0
                        guide_list.append(guide_weight)
                    
                    st.session_state.workout_queue.append({
                        "Category": str(row.get('Category', 'Accessory')),
                        "Exercise": row['Exercise'],
                        "Sets": n_sets,
                        "Rep_List": rep_list,
                        "Guide_List": guide_list,
                        "Meta": {
                            "Template": selected_template,
                            "Week": selected_week,
                            "Day": selected_day
                        }
                    })
                st.rerun()

# ==========================================
# 6. ACTIVE WORKOUT DISPLAY (HORIZONTAL LAYOUT)
# ==========================================
if st.session_state.workout_queue:
    logs_to_save = []
    
    for i, exercise in enumerate(st.session_state.workout_queue):
        with st.expander(f"**{exercise['Exercise']}** • {exercise['Sets']} sets", expanded=True):
            # Exercise header with fill button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"*{exercise.get('Category', 'Exercise')}*")
            with col2:
                if st.button("📋 Fill", key=f"fill_{i}", use_container_width=True):
                    copy_plan_to_actual(i, exercise['Sets'])
                    st.rerun()
            
            # HEADER ROW - All in one line
            header_html = """
            <div class="horizontal-layout">
                <div class="horizontal-cell"><span class="header-label">SET</span></div>
                <div class="horizontal-cell"><span class="header-label">TARGET</span></div>
                <div class="horizontal-cell"><span class="header-label">REPS</span></div>
                <div class="horizontal-cell"><span class="header-label">ACTUAL</span></div>
                <div class="horizontal-cell"><span class="header-label">REPS</span></div>
                <div class="horizontal-cell"><span class="header-label">RPE</span></div>
            </div>
            """
            st.markdown(header_html, unsafe_allow_html=True)
            
            # DATA ROWS - One horizontal row per set
            for set_num in range(exercise['Sets']):
                # Get target values for this set
                target_weight = exercise['Guide_List'][set_num] if set_num < len(exercise['Guide_List']) else exercise['Guide_List'][-1]
                target_reps = exercise['Rep_List'][set_num] if set_num < len(exercise['Rep_List']) else exercise['Rep_List'][-1]
                
                # Initialize session state if not exists
                weight_key = f"w_{i}_{set_num}"
                reps_key = f"r_{i}_{set_num}"
                rpe_key = f"rpe_{i}_{set_num}"
                
                if weight_key not in st.session_state:
                    st.session_state[weight_key] = 0.0
                if reps_key not in st.session_state:
                    st.session_state[reps_key] = 0
                if rpe_key not in st.session_state:
                    st.session_state[rpe_key] = 0.0
                
                # Create a single row for this set using Streamlit columns
                # This is the key to preventing stacking
                row_cols = st.columns([0.08, 0.23, 0.23, 0.23, 0.115, 0.115])
                
                with row_cols[0]:
                    # Set number
                    st.markdown(f"<div class='set-number'>{set_num+1}</div>", unsafe_allow_html=True)
                
                with row_cols[1]:
                    # Target weight display
                    st.markdown(f"<div class='target-box'>{int(target_weight)}</div>", unsafe_allow_html=True)
                
                with row_cols[2]:
                    # Target reps display
                    st.markdown(f"<div class='target-box reps-box'>{target_reps}</div>", unsafe_allow_html=True)
                
                with row_cols[3]:
                    # Actual weight input
                    actual_weight = st.number_input(
                        "Weight",
                        value=float(st.session_state[weight_key]),
                        min_value=0.0,
                        max_value=1000.0,
                        step=5.0,
                        key=weight_key,
                        label_visibility="collapsed",
                        format="%d"  # Display as integer
                    )
                    st.session_state[weight_key] = actual_weight
                
                with row_cols[4]:
                    # Actual reps input
                    actual_reps = st.number_input(
                        "Reps",
                        value=int(st.session_state[reps_key]),
                        min_value=0,
                        max_value=100,
                        step=1,
                        key=reps_key,
                        label_visibility="collapsed"
                    )
                    st.session_state[reps_key] = actual_reps
                
                with row_cols[5]:
                    # RPE input
                    actual_rpe = st.number_input(
                        "RPE",
                        value=float(st.session_state[rpe_key]),
                        min_value=0.0,
                        max_value=10.0,
                        step=0.5,
                        key=rpe_key,
                        label_visibility="collapsed",
                        format="%.1f"
                    )
                    st.session_state[rpe_key] = actual_rpe
                
                # Store log entry
                logs_to_save.append({
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Exercise": exercise['Exercise'],
                    "Set": set_num + 1,
                    "Weight": actual_weight,
                    "Reps": actual_reps,
                    "RPE": actual_rpe
                })
                
                # Small spacer between sets
                if set_num < exercise['Sets'] - 1:
                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    
    # Save button at the bottom
    st.markdown("---")
    if st.button("✅ Save Workout", type="primary", use_container_width=True):
        # Filter out empty entries
        valid_logs = [log for log in logs_to_save if log['Weight'] > 0]
        
        if valid_logs:
            try:
                new_logs_df = pd.DataFrame(valid_logs)
                
                # Read existing logs
                current_logs = conn.read(worksheet="Logs", ttl=0, dtype=str)
                if current_logs.empty:
                    current_logs = pd.DataFrame(columns=new_logs_df.columns)
                
                # Combine and save
                updated_logs = pd.concat([current_logs, new_logs_df], ignore_index=True)
                conn.update(worksheet="Logs", data=updated_logs)
                
                st.success("✅ Workout saved successfully!")
                st.session_state.workout_queue = []
                st.rerun()
            except Exception as e:
                st.error(f"Error saving workout: {str(e)}")
        else:
            st.warning("No data to save. Please log at least one set.")