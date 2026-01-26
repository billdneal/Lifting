import streamlit as st
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# ==========================================
# 1. CORE LOGIC & CONFIG
# ==========================================
st.set_page_config(page_title="5/3/1 SmartLog", page_icon="💪", layout="wide")

# RTS Table for Auto-Regulation
RTS_TABLE = {
    10: {1: 1.000, 2: 0.955, 3: 0.922, 4: 0.892, 5: 0.863},
    9.5: {1: 0.978, 2: 0.939, 3: 0.907, 4: 0.878, 5: 0.850},
    9:  {1: 0.955, 2: 0.922, 3: 0.892, 4: 0.863, 5: 0.837},
    8.5: {1: 0.939, 2: 0.907, 3: 0.878, 4: 0.850, 5: 0.824},
    8:  {1: 0.922, 2: 0.892, 3: 0.863, 4: 0.837, 5: 0.811},
    7.5: {1: 0.907, 2: 0.878, 3: 0.850, 4: 0.824, 5: 0.799},
    7:  {1: 0.892, 2: 0.863, 3: 0.837, 4: 0.811, 5: 0.786},
    6.5: {1: 0.878, 2: 0.850, 3: 0.824, 4: 0.799, 5: 0.774},
    6:  {1: 0.863, 2: 0.837, 3: 0.811, 4: 0.786, 5: 0.762}
}

@dataclass
class ExerciseVariant:
    base_lift: str
    modifiers: List[str] = field(default_factory=list)
    
    def display_name(self) -> str:
        if not self.modifiers:
            return self.base_lift
        return f"{' '.join(self.modifiers)} {self.base_lift}"

@dataclass
class SetLog:
    set_id: int
    planned_weight: float
    target_reps: str # Str because "5+"
    actual_weight: float = 0.0
    actual_reps: int = 0
    rpe: float = 0.0
    completed: bool = False

    def get_e1rm(self) -> Optional[float]:
        if self.actual_weight > 0 and self.actual_reps > 0 and self.rpe >= 6:
            # Simple lookup logic for RTS
            rpe_key = min(RTS_TABLE.keys(), key=lambda x: abs(x - self.rpe))
            rep_key = min(RTS_TABLE[rpe_key].keys(), key=lambda x: abs(x - self.actual_reps))
            pct = RTS_TABLE[rpe_key].get(rep_key, 1.0)
            return round(self.actual_weight / pct)
        return None

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def get_week_schedule(start_date, week_num):
    # Generates dates for the selected training week
    # Assuming start_date is Monday of Week 1
    week_start = start_date + timedelta(weeks=week_num-1)
    return {
        'Mon': week_start,
        'Wed': week_start + timedelta(days=2),
        'Fri': week_start + timedelta(days=4)
    }

def calculate_plate_math(weight):
    if weight < 45: return "Just Bar"
    rem = (weight - 45) / 2
    plates = []
    for p in [45, 25, 10, 5, 2.5]:
        while rem >= p:
            plates.append(str(p))
            rem -= p
    return "+".join(plates) if plates else "Bar"

# ==========================================
# 3. INTERFACE CONSTRUCTION
# ==========================================

st.title("📅 5/3/1 Training Calendar")

# --- Sidebar: Setup & Exercises ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. Exercise Library (Base + Modifiers)
    st.subheader("Exercise Builder")
    base_lift = st.selectbox("Base Lift", ["Squat", "Bench", "Deadlift", "Overhead Press", "Row"])
    modifiers = st.multiselect("Modifiers", ["Paused", "Tempo (3-0-3)", "SSB", "Deficit", "Pin", "Spoto"])
    
    current_variant = ExerciseVariant(base_lift, modifiers)
    st.info(f"Selected: **{current_variant.display_name()}**")
    
    st.divider()
    
    # 2. Program Settings
    current_week = st.selectbox("Current Week", range(1, 10), index=0)
    tm_squat = st.number_input("Squat TM", value=415)
    tm_bench = st.number_input("Bench TM", value=270)
    
# --- Top: Calendar Navigation ---
# We use columns to create a clickable "Week Strip"
schedule = get_week_schedule(datetime.now().date() - timedelta(days=datetime.now().weekday()), current_week)
selected_day = st.radio("Select Training Day:", list(schedule.keys()), horizontal=True, label_visibility="collapsed")

st.markdown(f"### {selected_day} - {schedule[selected_day].strftime('%b %d')}")
st.divider()

# ==========================================
# 4. WORKOUT LOGGER (The Core Feature)
# ==========================================

# Initialize Session State for the "Copy" feature
if "workout_data" not in st.session_state:
    st.session_state.workout_data = {}

# --- Generate "Planned" Data for the Day ---
# (In real app, this logic comes from your Program Class)
if selected_day == "Mon":
    focus_lift = "Squat"
    tm = tm_squat
elif selected_day == "Wed":
    focus_lift = "Bench"
    tm = tm_bench
else:
    focus_lift = "Deadlift"
    tm = 400

# Calculate specific weights for the selected week
percents = [0.65, 0.75, 0.85] if current_week == 1 else [0.70, 0.80, 0.90]
reps = [5, 5, "5+"]

# Create a unique key for this specific workout day
workout_key = f"w{current_week}_{selected_day}_{focus_lift}"

# Initialize this day's data if not exists
if workout_key not in st.session_state.workout_data:
    st.session_state.workout_data[workout_key] = [
        SetLog(i+1, round(tm*p/5)*5, r) for i, (p, r) in enumerate(zip(percents, reps))
    ]

# Get the data wrapper for editing
current_log = st.session_state.workout_data[workout_key]

# --- The "Main Work" Section ---
col_head, col_btn = st.columns([0.8, 0.2])
col_head.subheader(f"🏋️ {focus_lift} - Main Work")

# THE "FILL" BUTTON
if col_btn.button("⤵️ Fill Planned"):
    for s in current_log:
        s.actual_weight = s.planned_weight
    st.rerun()

# Build the Grid Layout manually (Streamlit's data_editor is harder to style for this specific need)
# Header Row
cols = st.columns([0.5, 1, 0.5, 1, 1, 1, 1])
cols[0].markdown("**Set**")
cols[1].markdown("**Planned**")
cols[2].markdown("➡️") # Arrow column
cols[3].markdown("**Actual (lbs)**")
cols[4].markdown("**Reps**")
cols[5].markdown("**RPE**")
cols[6].markdown("**e1RM**")

top_set_e1rm = 0

for i, set_data in enumerate(current_log):
    c = st.columns([0.5, 1, 0.5, 1, 1, 1, 1])
    
    # Set Number
    c[0].write(f"#{set_data.set_id}")
    
    # Planned
    c[1].write(f"**{set_data.planned_weight}** x {set_data.target_reps}")
    if i == 0: c[1].caption(calculate_plate_math(set_data.planned_weight))
    
    # Arrow (Visual only)
    c[2].write("⤵")
    
    # Actual Weight Input
    set_data.actual_weight = c[3].number_input(
        "Weight", 
        value=float(set_data.actual_weight), 
        key=f"{workout_key}_w_{i}", 
        label_visibility="collapsed"
    )
    
    # Reps Input
    set_data.actual_reps = c[4].number_input(
        "Reps", 
        value=int(set_data.actual_reps), 
        key=f"{workout_key}_r_{i}", 
        label_visibility="collapsed"
    )
    
    # RPE Input
    set_data.rpe = c[5].number_input(
        "RPE", 
        value=float(set_data.rpe), 
        step=0.5, 
        key=f"{workout_key}_rpe_{i}", 
        label_visibility="collapsed"
    )
    
    # Real-time e1RM Calc
    e1rm = set_data.get_e1rm()
    if e1rm:
        c[6].markdown(f"**{e1rm}**")
        if e1rm > top_set_e1rm: top_set_e1rm = e1rm
    else:
        c[6].write("-")

st.divider()

# --- Summary & Analytics ---
if top_set_e1rm > 0:
    st.success(f"🏆 **Session Best e1RM:** {top_set_e1rm} lbs")
    # This is where you would save to database:
    # update_max(focus_lift, top_set_e1rm)

with st.expander("➕ Add Accessory Exercise"):
    st.write("Use the Exercise Builder in the sidebar to define the lift, then click below.")
    if st.button("Add to Session"):
        st.toast(f"Added {current_variant.display_name()} to workout")

# Debug viewing of data structure (Remove in production)
# st.write(st.session_state.workout_data)
