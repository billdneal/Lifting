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
# Maps RPE -> Reps -> Percentage of 1RM
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
    tm_percent: float = 0.9

@dataclass
class SetData:
    id: int
    planned_weight: float
    target_reps: str
    actual_weight: float = 0.0
    actual_reps: int = 0
    rpe: float = 0.0
    
    def get_e1rm(self) -> float:
        """Calculate e1RM based on Actuals and RTS Table"""
        if self.actual_weight > 0 and self.actual_reps > 0 and self.rpe >= 6:
            # Find closest RPE key
            rpe_key = min(RTS_TABLE.keys(), key=lambda x: abs(x - self.rpe))
            # Find closest Rep key
            rep_key = min(RTS_TABLE[rpe_key].keys(), key=lambda x: abs(x - self.actual_reps))
            pct = RTS_TABLE[rpe_key][rep_key]
            return round(self.actual_weight / pct)
        return 0.0

def calculate_plate_math(weight):
    """Returns the plate loading for one side (45lb bar)"""
    if weight < 45: return "Bar"
    rem = (weight - 45) / 2
    plates = []
    for p in [45, 25, 10, 5, 2.5]:
        while rem >= p:
            plates.append(str(p))
            rem -= p
    return "+".join(plates) if plates else "Bar Only"

def get_block_info(week):
    """Returns Block Name and RPE Target based on Week 1-9"""
    if week <= 3:
        name = "5s Block (Hypertrophy/Volume)"
        if week == 1: rpe = "7-8 (2-3 RIR)"
        elif week == 2: rpe = "8 (2 RIR)"
        else: rpe = "8-9 (1 RIR)"
    elif week <= 6:
        name = "3s Block (Strength/Neural)"
        if week == 4: rpe = "8 (2 RIR)"
        elif week == 5: rpe = "8.5 (1-2 RIR)"
        else: rpe = "9 (1 RIR)"
    else:
        name = "Peak Block (Realization)"
        if week == 7: rpe = "9 (1 RIR)"
        elif week == 8: rpe = "9.5 (0-1 RIR)"
        else: rpe = "Deload / Test"
    return name, rpe

def generate_session(week, day, profile: UserProfile):
    """Generates the 5/3/1 Session Data"""
    # 1. Determine Lift & TM
    if day == "Mon":
        lift = "Squat"
        tm = profile.squat_max * profile.tm_percent
    elif day == "Wed":
        lift = "Bench"
        tm = profile.bench_max * profile.tm_percent
    else:
        lift = "Trap Bar Deadlift"
        tm = profile.deadlift_max * profile.tm_percent

    # Block Logic Adjustments (TM bumps for blocks 2 & 3)
    if week > 3: tm += (10 if lift != "Bench" else 5)
    if week > 6: tm += (10 if lift != "Bench" else 5)

    # 2. Determine Percentages
    # 5s Block
    if week <= 3:
        percents = [0.65, 0.75, 0.85]
        reps = [5, 5, "5+"]
        supp_scheme = "5x5 FSL"
        supp_pct = 0.65
    # 3s Block
    elif week <= 6:
        percents = [0.70, 0.80, 0.90]
        reps = [3, 3, "3+"]
        supp_scheme = "3x5 FSL"
        supp_pct = 0.70
    # Peak Block
    else: 
        percents = [0.75, 0.85, 0.95]
        reps = [5, 3, "1+"]
        supp_scheme = "3x3 SSL" # Second Set Last for peak
        supp_pct = 0.85

    # 3. Build Sets
    sets = []
    # Warmups
    warmups = [0.4, 0.5, 0.6]
    for i, p in enumerate(warmups):
        w = round((tm * p) / 5) * 5
        sets.append(SetData(id=-(2-i), planned_weight=w, target_reps="5"))

    # Main Work
    for i, p in enumerate(percents):
        w = round((tm * p) / 5) * 5
        sets.append(SetData(id=i+1, planned_weight=w, target_reps=str(reps[i])))
        
    return lift, sets, supp_scheme, round((tm * supp_pct)/5)*5

# ==========================================
# 3. STATE MANAGEMENT
# ==========================================
if 'view' not in st.session_state:
    st.session_state.view = 'calendar'
if 'selected_workout' not in st.session_state:
    st.session_state.selected_workout = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = UserProfile()

def navigate_to(view_name, workout_meta=None):
    st.session_state.view = view_name
    if workout_meta:
        st.session_state.selected_workout = workout_meta

def fill_planned_callback(session_key):
    """Callback to copy planned weights to actual inputs"""
    # This assumes specific key naming convention: "{session_key}_planned_{i}"
    # We iterate through session state to find matching keys
    for key in st.session_state:
        if key.startswith(f"{session_key}_actual_weight_"):
            index = key.split("_")[-1]
            planned_key = f"{session_key}_planned_{index}"
            # Copy planned value to actual
            if planned_key in st.session_state:
                st.session_state[key] = st.session_state[planned_key]

# ==========================================
# 4. UI: SIDEBAR & EXERCISE BUILDER
# ==========================================
with st.sidebar:
    st.header("👤 Profile")
    with st.expander("Edit Maxes", expanded=False):
        sq = st.number_input("Squat", value=465, step=5)
        bp = st.number_input("Bench", value=300, step=5)
        dl = st.number_input("Trap Bar DL", value=560, step=5)
        st.session_state.user_profile = UserProfile(sq, bp, dl)

    st.divider()
    
    st.header("🛠️ Exercise Builder")
    st.caption("Create custom lifts to add to your session.")
    base = st.selectbox("Base", ["Squat", "Bench", "Deadlift", "Press", "Row", "Lunge"])
    mods = st.multiselect("Modifiers", ["Paused", "SSB", "Tempo 3-0-3", "Pin", "Deficit", "Chain", "Band"])
    custom_name = f"{' '.join(mods)} {base}" if mods else base
    st.info(f"**{custom_name}**")
    
    if st.button("Add to Session"):
        if st.session_state.view == 'workout':
            # In a real database app, we'd append this to the DB
            st.toast(f"Added {custom_name} to today's workout")
        else:
            st.warning("Open a workout first!")

# ==========================================
# 5. UI: CALENDAR DASHBOARD (HOME)
# ==========================================
if st.session_state.view == 'calendar':
    st.title("📅 Training Calendar")
    
    # Week Selector
    c1, c2 = st.columns([1, 3])
    with c1:
        selected_week = st.selectbox("Select Week", range(1, 10), index=0)
    
    block_name, rpe_target = get_block_info(selected_week)
    
    with c2:
        st.info(f"**{block_name}**\n\nTarget Intensity: RPE {rpe_target}")

    st.divider()
    
    # Day Cards
    col1, col2, col3 = st.columns(3)
    
    days = [("Mon", "Squat Focus", "🦵"), ("Wed", "Bench Focus", "💪"), ("Fri", "Deadlift Focus", "🦍")]
    
    for i, (day_name, focus, icon) in enumerate(days):
        with [col1, col2, col3][i]:
            st.markdown(f"### {icon} {day_name}")
            st.caption(focus)
            
            # Preview the main lift weight
            lift, sets, _, _ = generate_session(selected_week, day_name, st.session_state.user_profile)
            top_set = sets[-1]
            st.markdown(f"**Top Set:** {top_set.planned_weight} lbs x {top_set.target_reps}")
            
            if st.button(f"Open {day_name}", key=f"btn_{selected_week}_{day_name}"):
                navigate_to('workout', {'week': selected_week, 'day': day_name})
                st.rerun()

# ==========================================
# 6. UI: WORKOUT LOGGER (ACTIVE SESSION)
# ==========================================
elif st.session_state.view == 'workout':
    meta = st.session_state.selected_workout
    week = meta['week']
    day = meta['day']
    
    if st.button("← Back to Calendar"):
        navigate_to('calendar')
        st.rerun()

    # Generate Logic
    lift_name, main_sets, supp_scheme, supp_weight = generate_session(week, day, st.session_state.user_profile)
    
    st.title(f"Week {week} • {day} • {lift_name}")
    
    # --- MAIN LIFT SECTION ---
    c_head, c_fill = st.columns([3, 1])
    c_head.subheader("🏋️ Main Lift")
    
    # Unique session key for state
    session_key = f"w{week}_{day}_{lift_name}"
    
    # THE FILL BUTTON
    if c_fill.button("⤵️ Fill Planned", key="fill_btn"):
        fill_planned_callback(session_key)
        st.rerun()

    # Header Row
    cols = st.columns([0.5, 1.5, 1.5, 1, 1, 1])
    cols[0].markdown("#")
    cols[1].markdown("**Planned**")
    cols[2].markdown("**Actual (lbs)**")
    cols[3].markdown("**Reps**")
    cols[4].markdown("**RPE**")
    cols[5].markdown("**e1RM**")
    
    best_e1rm = 0

    for i, s in enumerate(main_sets):
        # Determine row color (warmup vs work)
        bg_color = "rgba(255,255,255,0.05)" if s.id > 0 else "transparent"
        
        with st.container():
            c = st.columns([0.5, 1.5, 1.5, 1, 1, 1])
            
            # ID
            c[0].write(f"{'Warm' if s.id < 1 else s.id}")
            
            # Planned (Text + Plate Math)
            c[1].markdown(f"**{s.planned_weight}** x {s.target_reps}")
            c[1].caption(calculate_plate_math(s.planned_weight))
            
            # Hidden storage for "Fill" logic
            st.session_state[f"{session_key}_planned_{i}"] = s.planned_weight
            
            # Actual Weight Input
            act_w = c[2].number_input(
                "W", value=0.0, step=5.0, 
                key=f"{session_key}_actual_weight_{i}", 
                label_visibility="collapsed"
            )
            
            # Actual Reps
            act_r = c[3].number_input(
                "R", value=int(s.target_reps) if isinstance(s.target_reps, int) else 5, 
                key=f"{session_key}_actual_reps_{i}", 
                label_visibility="collapsed"
            )
            
            # RPE
            act_rpe = c[4].number_input(
                "RPE", value=0.0, step=0.5, 
                key=f"{session_key}_actual_rpe_{i}", 
                label_visibility="collapsed"
            )
            
            # Live e1RM
            live_set = SetData(s.id, s.planned_weight, s.target_reps, act_w, act_r, act_rpe)
            e1rm = live_set.get_e1rm()
            
            if e1rm > 0:
                c[5].markdown(f"**{int(e1rm)}**")
                if s.id > 0 and e1rm > best_e1rm: best_e1rm = e1rm
            else:
                c[5].write("-")

    st.divider()
    
    if best_e1rm > 0:
        st.success(f"🏆 **Session Best e1RM:** {int(best_e1rm)} lbs")

    # --- SUPPLEMENTAL SECTION ---
    st.subheader(f"🏗️ Supplemental: {supp_scheme}")
    st.info(f"Target: **{supp_weight} lbs**")
    
    col_supp = st.columns(5)
    for i in range(5):
        col_supp[i].checkbox(f"Set {i+1}", key=f"{session_key}_supp_{i}")

    # --- ACCESSORY SECTION ---
    st.subheader("💪 Accessories")
    st.caption("Target: 50 reps total per category")
    
    acc_cols = st.columns(3)
    with acc_cols[0]:
        st.markdown("**Push**")
        st.text_area("Log", placeholder="e.g., DB Bench 3x12 @ 60s", height=100, key=f"{session_key}_acc_push")
    with acc_cols[1]:
        st.markdown("**Pull**")
        st.text_area("Log", placeholder="e.g., Rows 4x10 @ 135", height=100, key=f"{session_key}_acc_pull")
    with acc_cols[2]:
        st.markdown("**Legs/Core**")
        st.text_area("Log", placeholder="e.g., Plank 3x60s", height=100, key=f"{session_key}_acc_core")

    st.button("✅ Complete Workout", type="primary")
