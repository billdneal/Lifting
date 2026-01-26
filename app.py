import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional

# ==========================================
# 1. DATABASE: EXERCISES & MODIFIERS
# ==========================================
st.set_page_config(page_title="Advanced 5/3/1 Block", page_icon="🏋️", layout="wide")

# This is the list you can expand later!
LIFT_DB = {
    "Squat Pattern": ["Squat", "SSB Squat", "Front Squat", "Box Squat", "Split Squat", "Leg Press"],
    "Bench Pattern": ["Bench Press", "DB Bench", "Incline Bench", "Floor Press", "Overhead Press"],
    "Deadlift Pattern": ["Trap Bar Deadlift", "Conventional Deadlift", "Sumo Deadlift", "RDL", "Stiff Leg DL"],
    "Upper Pull": ["Barbell Row", "DB Row", "Pull-ups", "Lat Pulldown", "Face Pulls", "Chest Supported Row"],
    "Accessories": ["Triceps Extension", "Bicep Curls", "Leg Curls", "Leg Extensions", "Calf Raises", "Plank", "Ab Wheel"]
}

MODIFIER_DB = {
    "Tempo / Pause": ["Paused (2ct)", "Paused (3ct)", "Tempo 3-0-3", "Tempo 5-0-0", "Dead Stop"],
    "Range of Motion": ["Pin Press", "Board Press", "Deficit", "Block Pull", "Spoto", "High Handle"],
    "Resistance / Load": ["Bands (Light)", "Bands (Average)", "Chains", "Weight Vest"],
    "Stance / Grip": ["Close Grip", "Wide Grip", "Snatch Grip", "Fat Grip"]
}

# RTS RPE Table
RTS_TABLE = {
    10: {1: 1.000, 2: 0.955, 3: 0.922, 4: 0.892, 5: 0.863, 6: 0.837, 7: 0.811, 8: 0.786},
    9.5: {1: 0.978, 2: 0.939, 3: 0.907, 4: 0.878, 5: 0.850, 6: 0.824, 7: 0.799, 8: 0.774},
    9:  {1: 0.955, 2: 0.922, 3: 0.892, 4: 0.863, 5: 0.837, 6: 0.811, 7: 0.786, 8: 0.762},
    8.5: {1: 0.939, 2: 0.907, 3: 0.878, 4: 0.850, 5: 0.824, 6: 0.799, 7: 0.774, 8: 0.751},
    8:  {1: 0.922, 2: 0.892, 3: 0.863, 4: 0.837, 5: 0.811, 6: 0.786, 7: 0.762, 8: 0.739},
    7:  {1: 0.892, 2: 0.863, 3: 0.837, 4: 0.811, 5: 0.786, 6: 0.762, 7: 0.739, 8: 0.717},
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

def get_block_info(week):
    if week <= 3: return "5s Block (Volume)", "7-8 (2-3 RIR)"
    elif week <= 6: return "3s Block (Strength)", "8-9 (1-2 RIR)"
    else: return "Peak Block (Realization)", "9-10 (0-1 RIR)"

def generate_session(week, day, profile: UserProfile):
    # Determines the Main Lift based on Day
    if day == "Mon": lift = "Squat"
    elif day == "Wed": lift = "Bench Press"
    else: lift = "Trap Bar Deadlift"
    
    tm = profile.get_tm(lift)
    # Block Logic TM Bumps
    if week > 3: tm += (10 if "Bench" not in lift else 5)
    if week > 6: tm += (10 if "Bench" not in lift else 5)

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

if 'added_accessories' not in st.session_state:
    st.session_state.added_accessories = []

def navigate_to(view_name, workout_meta=None):
    st.session_state.view = view_name
    if workout_meta:
        st.session_state.selected_workout = workout_meta
        st.session_state.added_accessories = []

def fill_planned_callback(session_key):
    for key in st.session_state:
        if key.startswith(f"{session_key}_actual_weight_"):
            index = key.split("_")[-1]
            planned_key = f"{session_key}_planned_{index}"
            if planned_key in st.session_state:
                st.session_state[key] = st.session_state[planned_key]
