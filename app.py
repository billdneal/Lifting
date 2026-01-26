import streamlit as st
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

# ==========================================
# 1. CONFIG & RTS DATA
# ==========================================
st.set_page_config(page_title="Advanced 5/3/1 Block", page_icon="🏋️", layout="wide")

# RTS RPE Table (Tuchscherer)
RTS_TABLE = {
    10: {1: 1.000, 2: 0.955, 3: 0.922, 4: 0.892, 5: 0.863, 6: 0.837, 7: 0.811, 8: 0.786},
    9.5: {1: 0.978, 2: 0.939, 3: 0.907, 4: 0.878, 5: 0.850, 6: 0.824, 7: 0.799, 8: 0.774},
    9:  {1: 0.955, 2: 0.922, 3: 0.892, 4: 0.863, 5: 0.837, 6: 0.811, 7: 0.786, 8: 0.762},
    8.5: {1: 0.939, 2: 0.907, 3: 0.878, 4: 0.850, 5: 0.824, 6: 0.799, 7: 0.774, 8: 0.751},
    8:  {1: 0.922, 2: 0.892, 3: 0.863, 4: 0.837, 5: 0.811, 6: 0.786, 7: 0.762, 8: 0.739},
    7.5: {1: 0.907, 2: 0.878, 3: 0.850, 4: 0.824, 5: 0.799, 6: 0.774, 7: 0.751, 8: 0.728},
    7:  {1: 0.892, 2: 0.863, 3: 0.837, 4: 0.811, 5: 0.786, 6: 0.762, 7: 0.739, 8: 0.717},
    6.5: {1: 0.878, 2: 0.850, 3: 0.824, 4: 0.799, 5: 0.774, 6: 0.751, 7: 0.728, 8: 0.706},
    6:  {1: 0.863, 2: 0.837, 3: 0.811, 4: 0.786, 5: 0.762, 6: 0.739, 7: 0.717, 8: 0.696}
}

# ==========================================
# 2. CLASSES & LOGIC
# ==========================================

@dataclass
class UserProfile:
    squat_max: int = 465
    bench_max: int = 300
    deadlift_max: int = 560
    press_max: int = 185
    tm_percent: float = 0.9
    
    def get_tm(self, lift_name):
        if "Squat" in lift_name: return self.squat_max * self.tm_percent
        if "Bench" in lift_name: return self.bench_max * self.tm_percent
        if "Deadlift" in lift_name: return self.deadlift_max * self.tm_percent
        if "Press" in lift_name: return self.press_max * self.tm_percent
        return 0

@dataclass
class SetData:
    id: int
    planned_weight: float
    target_reps: str
    actual_weight: float = 0.0
    actual_reps: int = 0
    rpe: float = 0.0
    
    def get_e1rm(self) -> float:
        if self.actual_weight > 0 and self.actual_reps > 0 and self.rpe >= 6:
            rpe_key = min(RTS_TABLE.keys(), key=lambda x: abs(x - self.rpe))
            rep_key = min(RTS_TABLE[rpe_key].keys(), key=lambda x: abs(x - self.actual_reps))
            pct = RTS_TABLE[rpe_key].get(rep_key, 1.0)
            return round(self.actual_weight / pct)
        return 0.0

def calculate_plate_math(weight):
    if weight < 45: return "Bar"
    rem = (weight - 45) / 2
    plates = []
    for p in [45, 25, 10, 5, 2.5]:
        while rem >= p:
            plates.append(str(p))
            rem -= p
    return "+".join(plates) if plates else "Bar"

def get_block_info(week):
    if week <= 3:
        return "5s Block (Volume)", "7-8 (2-3 RIR)"
    elif week <= 6:
        return "3s Block (Strength)", "8-9 (1-2 RIR)"
    else:
        return "Peak Block (Realization)", "9-10 (0-1 RIR)"

def generate_session(week, day, profile: UserProfile):
    # 1. Determine Lift
    if day == "Mon": lift = "Squat"
    elif day == "Wed": lift = "Bench"
    else: lift = "Deadlift"
    
    tm = profile.get_tm(lift)

    # Block Logic (TM bumps)
    if week > 3: tm += (10 if lift != "Bench" else 5)
    if week > 6: tm += (10 if lift != "Bench" else 5)

    # 2. Determine Percentages
    if week <= 3:
        percents = [0.65, 0.75, 0.85]
        reps = [5, 5, "5+"]
        supp_scheme = "5x5 FSL"
        supp_pct = 0.65
    elif week <= 6:
        percents = [0.70, 0.80, 0.90]
        reps = [3, 3, "3+"]
        supp_scheme = "3x5 FSL"
        supp_pct = 0.70
    else: 
        percents = [0.75, 0.85, 0.95]
        reps = [5, 3, "1+"]
        supp_scheme = "3x3 SSL"
        supp_pct = 0.85

    # 3. Build Main Sets
    sets = []
    # Warmups
    for i, p in enumerate([0.4, 0.5, 0.6]):
        w = round((tm * p) / 5) * 5
        sets.append(SetData(id=-(2-i), planned_weight=w, target_reps="5"))
    # Work
    for i, p in enumerate(percents):
        w = round((tm * p) / 5) * 5
        sets.append(SetData(id=i+1, planned_weight=w, target_reps=str(reps[i])))
        
    return lift, sets, supp_scheme, supp_pct

# ==========================================
# 3. STATE MANAGEMENT
# ==========================================
if 'view' not in st.session_state:
    st.session_state.view = 'calendar'
if 'selected_workout' not in st.session_state:
    st.session_state.selected_workout = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = UserProfile()

# Initialize Accessory Data Frame in session state if not exists
if 'acc_data' not in st.session_state:
    st.session_state.acc_data = pd.DataFrame(columns=["Exercise", "Weight", "Reps", "RPE"])

def navigate_to(view_name, workout_meta=None):
    st.session_state.view = view_name
    if workout_meta:
        st.session_state.selected_workout = workout_meta

def fill_planned_callback(session_key):
    for key in st.session_state:
        if key.startswith(f"{session_key}_actual_weight_"):
            index = key.split("_")[-1]
            planned_key = f"{session_key}_planned_{index}"
            if planned_key in st.session_state:
                st.session_state[key] = st.session_state[planned_key]

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("👤 Profile")
    with st.expander("Edit Maxes", expanded=False):
        sq = st.number_input("Squat", value=465, step=5)
        bp = st.number_input("Bench", value=300, step=5)
        dl = st.number_input("Trap Bar DL", value=560, step=5)
        pr = st.number_input("Overhead Press", value=185, step=5)
        st.session_state.user_profile = UserProfile(sq, bp, dl, pr)

    st.divider()
    st.info("💡 **Tip:** Use the 'Fill Planned' button to instantly copy target weights to actuals.")

# ==========================================
# 5. CALENDAR VIEW
# ==========================================
if st.session_state.view == 'calendar':
    st.title("📅 Training Calendar")
    
    c1, c2 = st.columns([1, 3])
    with c1:
        selected_week = st.selectbox("Select Week", range(1, 10), index=0)
    
    block_name, rpe_target = get_block_info(selected_week)
    with c2:
        st.info(f"**{block_name}**\n\nTarget Intensity: RPE {rpe_target}")

    st.divider()
    col1, col2, col3 = st.columns(3)
    days = [("Mon", "Squat Focus", "🦵"), ("Wed", "Bench Focus", "💪"), ("Fri", "Deadlift Focus", "🦍")]
    
    for i, (day_name, focus, icon) in enumerate(days):
        with [col1, col2, col3][i]:
            st.markdown(f"### {icon} {day_name}")
            st.caption(focus)
            lift, sets, _, _ = generate_session(selected_week, day_name, st.session_state.user_profile)
            top_set = sets[-1]
            st.markdown(f"**Top Set:** {top_set.planned_weight} lbs x {top_set.target_reps}")
            if st.button(f"Open {day_name}", key=f"btn_{selected_week}_{day_name}"):
                navigate_to('workout', {'week': selected_week, 'day': day_name})
                st.rerun()

# ==========================================
# 6. WORKOUT VIEW (FULL LOGGING)
# ==========================================
elif st.session_state.view == 'workout':
    meta = st.session_state.selected_workout
    week = meta['week']
    day = meta['day']
    
    if st.button("← Back to Calendar"):
        navigate_to('calendar')
        st.rerun()

    lift_name, main_sets, supp_scheme_name, supp_pct = generate_session(week, day, st.session_state.user_profile)
    session_key = f"w{week}_{day}_{lift_name}"
    
    st.title(f"Week {week} • {day} • {lift_name}")

    # --- SECTION 1: MAIN LIFT ---
    c_head, c_fill = st.columns([3, 1])
    c_head.subheader(f"1️⃣ Main Lift: {lift_name}")
    if c_fill.button("⤵️ Fill Planned", key="fill_btn"):
        fill_planned_callback(session_key)
        st.rerun()

    cols = st.columns([0.5, 1.5, 1.5, 1, 1, 1])
    cols[1].markdown("**Planned**")
    cols[2].markdown("**Actual (lbs)**")
    cols[3].markdown("**Reps**")
    cols[4].markdown("**RPE**")
    cols[5].markdown("**e1RM**")
    
    best_e1rm = 0

    for i, s in enumerate(main_sets):
        # Warmup styling (grayed out ID)
        with st.container():
            c = st.columns([0.5, 1.5, 1.5, 1, 1, 1])
            c[0].write(f"{'Warm' if s.id < 1 else s.id}")
            c[1].markdown(f"**{s.planned_weight}** x {s.target_reps}")
            c[1].caption(calculate_plate_math(s.planned_weight))
            st.session_state[f"{session_key}_planned_{i}"] = s.planned_weight
            
            act_w = c[2].number_input("W", value=0.0, step=5.0, key=f"{session_key}_actual_weight_{i}", label_visibility="collapsed")
            act_r = c[3].number_input("R", value=int(s.target_reps) if isinstance(s.target_reps, int) else 5, key=f"{session_key}_actual_reps_{i}", label_visibility="collapsed")
            act_rpe = c[4].number_input("RPE", value=0.0, step=0.5, key=f"{session_key}_actual_rpe_{i}", label_visibility="collapsed")
            
            live_set = SetData(s.id, s.planned_weight, s.target_reps, act_w, act_r, act_rpe)
            e1rm = live_set.get_e1rm()
            if e1rm > 0:
                c[5].markdown(f"**{int(e1rm)}**")
                if s.id > 0 and e1rm > best_e1rm: best_e1rm = e1rm
            else:
                c[5].write("-")

    if best_e1rm > 0:
        st.success(f"🏆 **Session Best e1RM:** {int(best_e1rm)} lbs")

    st.divider()

    # --- SECTION 2: SUPPLEMENTAL ---
    st.subheader(f"2️⃣ Supplemental")
    
    # Selector for Lift (Defaults to same as main, but changeable)
    col_sel, col_info = st.columns([1, 2])
    supp_lift = col_sel.selectbox("Lift", ["Squat", "Bench", "Deadlift", "Overhead Press"], index=["Squat", "Bench", "Deadlift", "Overhead Press"].index(lift_name) if lift_name in ["Squat", "Bench", "Deadlift", "Overhead Press"] else 0)
    
    # Calculate Target Weight based on selection
    supp_tm = st.session_state.user_profile.get_tm(supp_lift)
    # Adjust TM for blocks 2/3 manually just for display calculation
    if week > 3: supp_tm += (10 if "Bench" not in supp_lift and "Press" not in supp_lift else 5)
    target_w = round((supp_tm * supp_pct) / 5) * 5
    
    col_info.info(f"**Protocol:** {supp_scheme_name}  |  **Target:** {target_w} lbs")

    # Logging Grid for Supplemental
    supp_cols = st.columns([1, 1, 1])
    supp_cols[0].markdown("**Weight**")
    supp_cols[1].markdown("**Reps**")
    supp_cols[2].markdown("**RPE**")
    
    for j in range(5): # 5 Sets standard
        r = st.columns([1, 1, 1])
        r[0].number_input("W", value=float(target_w), step=5.0, key=f"{session_key}_supp_w_{j}", label_visibility="collapsed")
        r[1].number_input("R", value=5, key=f"{session_key}_supp_r_{j}", label_visibility="collapsed")
        r[2].number_input("RPE", value=0.0, step=0.5, key=f"{session_key}_supp_rpe_{j}", label_visibility="collapsed")

    st.divider()

    # --- SECTION 3: ACCESSORIES ---
    st.subheader("3️⃣ Accessories")
    st.caption("Log as many exercises and sets as needed.")

    # Initialize dataframe for this specific session if empty
    if f"{session_key}_acc_df" not in st.session_state:
        st.session_state[f"{session_key}_acc_df"] = pd.DataFrame(
            [{"Exercise": "DB Bench", "Weight": 60, "Reps": 12, "RPE": 8}], # Example row
        )

    # Editable Dataframe
    edited_df = st.data_editor(
        st.session_state[f"{session_key}_acc_df"],
        num_rows="dynamic",
        column_config={
            "Exercise": st.column_config.TextColumn("Exercise", width="medium"),
            "Weight": st.column_config.NumberColumn("Lbs", step=5),
            "Reps": st.column_config.NumberColumn("Reps", step=1),
            "RPE": st.column_config.NumberColumn("RPE", step=0.5)
        },
        use_container_width=True,
        key=f"{session_key}_acc_editor"
    )
    
    # Save back to state (Streamlit does this automatically via the key, but good to know)
    
    st.divider()
    if st.button("✅ Finish Workout", type="primary"):
        st.balloons()
        st.success("Workout Saved! (Data persists in session)")
