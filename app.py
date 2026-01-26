import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional

# ==========================================
# 1. CONFIG & DATABASES
# ==========================================
st.set_page_config(page_title="Advanced 5/3/1 Block", page_icon="🏋️", layout="wide")

# Exercise Library
LIFT_DB = {
    "Squat Pattern": ["Squat", "SSB Squat", "Front Squat", "Box Squat", "Split Squat", "Leg Press"],
    "Bench Pattern": ["Bench Press", "DB Bench", "Incline Bench", "Floor Press", "Overhead Press"],
    "Deadlift Pattern": ["Trap Bar Deadlift", "Conventional Deadlift", "Sumo Deadlift", "RDL", "Stiff Leg DL"],
    "Upper Pull": ["Barbell Row", "DB Row", "Pull-ups", "Lat Pulldown", "Face Pulls", "Chest Supported Row"],
    "Accessories": ["Triceps Extension", "Bicep Curls", "Leg Curls", "Leg Extensions", "Calf Raises", "Plank", "Ab Wheel"]
}

# Flattened list of all modifiers for dropdowns
ALL_MODS = [
    "Paused", "Tempo 3-0-3", "Pin Press", "Board Press", "Deficit", 
    "Block Pull", "Spoto", "Bands", "Chains", "Close Grip", 
    "Wide Grip", "Snatch Grip", "Fat Grip", "SSB", "Cambered Bar"
]

MODIFIER_DB = {
    "Tempo / Pause": ["Paused", "Tempo 3-0-3", "Tempo 5-0-0", "Dead Stop"],
    "ROM": ["Pin Press", "Board Press", "Deficit", "Block Pull", "Spoto"],
    "Resistance": ["Bands", "Chains", "Weight Vest"],
    "Bar/Grip": ["Close Grip", "Wide Grip", "Snatch Grip", "Fat Grip", "SSB"]
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
        # Allow partial matches for pivots (e.g. "SSB Squat" uses "Squat" Max)
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
            if self.actual_reps in RTS_TABLE[rpe_key]:
                pct = RTS_TABLE[rpe_key][self.actual_reps]
            else:
                pct = RTS_TABLE[rpe_key].get(min(RTS_TABLE[rpe_key].keys(), key=lambda x: abs(x - self.actual_reps)))
            return round(self.actual_weight / pct)
        return 0.0

def get_block_info(week):
    if week <= 3: return "5s Block (Volume)", "7-8 (2-3 RIR)"
    elif week <= 6: return "3s Block (Strength)", "8-9 (1-2 RIR)"
    else: return "Peak Block (Realization)", "9-10 (0-1 RIR)"

def generate_session(week, day, profile: UserProfile, lift_override=None, tm_modifier=1.0):
    # Determine Main Lift (or use override)
    if lift_override:
        lift = lift_override
    else:
        if day == "Mon": lift = "Squat"
        elif day == "Wed": lift = "Bench Press"
        else: lift = "Trap Bar Deadlift"
    
    tm = profile.get_tm(lift)
    
    # Block Logic TM Bumps
    if week > 3: tm += (10 if "Bench" not in lift else 5)
    if week > 6: tm += (10 if "Bench" not in lift else 5)
    
    # Apply Pivot Modifier (e.g. 0.9 for a harder variation)
    tm = tm * tm_modifier

    # Percentage Logic
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
    # Work Sets
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

# ==========================================
# 4. SIDEBAR: PROFILE & EXERCISE BUILDER
# ==========================================
with st.sidebar:
    st.header("👤 Profile")
    with st.expander("Edit Maxes"):
        sq = st.number_input("Squat", value=465, step=5)
        bp = st.number_input("Bench", value=300, step=5)
        dl = st.number_input("Trap Bar DL", value=560, step=5)
        pr = st.number_input("Overhead Press", value=185, step=5)
        st.session_state.user_profile = UserProfile(sq, bp, dl, pr)

    st.divider()
    
    st.header("🛠️ Exercise Builder")
    st.caption("Construct a lift and add it to today's session.")
    
    # Category Selection
    cat_select = st.selectbox("Category", list(LIFT_DB.keys()))
    base_select = st.selectbox("Base Lift", LIFT_DB[cat_select])
    
    # Modifiers
    selected_mods = []
    with st.expander("Modifiers (Optional)"):
        for mod_cat, mod_list in MODIFIER_DB.items():
            st.markdown(f"**{mod_cat}**")
            cols = st.columns(2)
            for i, mod in enumerate(mod_list):
                if cols[i % 2].checkbox(mod, key=f"mod_{mod}"):
                    selected_mods.append(mod)
    
    final_name = f"{' '.join(selected_mods)} {base_select}".strip()
    st.info(f"**{final_name}**")
    
    if st.button("➕ Add to Session", type="primary"):
        if st.session_state.view == 'workout':
            st.session_state.added_accessories.append(final_name)
            st.toast(f"Added {final_name}!")
        else:
            st.warning("Please open a workout first.")

# ==========================================
# 5. VIEW: CALENDAR DASHBOARD
# ==========================================
if st.session_state.view == 'calendar':
    st.title("📅 Training Calendar")
    
    c1, c2 = st.columns([1, 3])
    with c1: selected_week = st.selectbox("Select Week", range(1, 10))
    block_name, rpe_target = get_block_info(selected_week)
    with c2: st.info(f"**{block_name}**\n\nTarget: RPE {rpe_target}")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    days = [("Mon", "Squat Focus", "🦵"), ("Wed", "Bench Focus", "💪"), ("Fri", "Deadlift Focus", "🦍")]
    
    for i, (day_name, focus, icon) in enumerate(days):
        with [col1, col2, col3][i]:
            st.markdown(f"### {icon} {day_name}")
            st.caption(focus)
            if st.button(f"Open {day_name}", key=f"btn_{selected_week}_{day_name}"):
                navigate_to('workout', {'week': selected_week, 'day': day_name})
                st.rerun()

# ==========================================
# 6. VIEW: WORKOUT LOGGER
# ==========================================
elif st.session_state.view == 'workout':
    meta = st.session_state.selected_workout
    week, day = meta['week'], meta['day']
    
    # --- PIVOT / CUSTOMIZE LOGIC ---
    # Determine default lift first
    if day == "Mon": default_lift = "Squat"
    elif day == "Wed": default_lift = "Bench Press"
    else: default_lift = "Trap Bar Deadlift"

    # UI for Pivot
    with st.sidebar:
        st.divider()
        st.header("⚙️ Pivot / Customize")
        st.caption("Need to swap the main lift or add modifiers?")
        
        # 1. Base Lift Swap
        pivot_base = st.selectbox(
            "Main Lift Base", 
            LIFT_DB["Squat Pattern"] + LIFT_DB["Bench Pattern"] + LIFT_DB["Deadlift Pattern"],
            index=0 if default_lift == "Squat" else (1 if default_lift == "Bench Press" else 2) 
        )
        
        # 2. Modifiers
        pivot_mods = st.multiselect("Main Lift Modifiers", ALL_MODS)
        
        # 3. TM Adjustment
        tm_adj = st.slider("Training Max %", 50, 120, 100, 5, help="Lower this if doing a harder variation (e.g. Front Squat)")
    
    # Re-Generate Session with Overrides
    full_lift_name = f"{' '.join(pivot_mods)} {pivot_base}".strip()
    _, main_sets, supp_scheme, supp_pct = generate_session(
        week, day, st.session_state.user_profile, 
        lift_override=pivot_base, 
        tm_modifier=tm_adj/100
    )
    
    session_key = f"w{week}_{day}_{full_lift_name}"
    
    if st.button("← Back to Calendar"):
        navigate_to('calendar')
        st.rerun()
        
    st.title(f"{day} • {full_lift_name}")

    # --- MAIN LIFT ---
    c_head, c_fill = st.columns([3, 1])
    c_head.subheader(f"1️⃣ Main Work")
    if c_fill.button("⤵️ Fill Planned"):
        fill_planned_callback(session_key)
        st.rerun()

    # Warmups
    warmups = [s for s in main_sets if s.id < 1]
    if warmups:
        with st.expander("🔥 Warmup Sets (Read Only)", expanded=False):
            w_df = pd.DataFrame([{"Weight": s.planned_weight, "Reps": 5} for s in warmups])
            st.table(w_df)

    # Work Sets
    work_sets = [s for s in main_sets if s.id > 0]
    cols = st.columns([0.5, 1.5, 1.5, 1, 1, 1])
    cols[1].markdown("**Planned**")
    cols[2].markdown("**Actual**")
    cols[3].markdown("**Reps**")
    cols[4].markdown("**RPE**")
    cols[5].markdown("**e1RM**")

    best_e1rm = 0
    for i, s in enumerate(work_sets):
        st.session_state[f"{session_key}_planned_{i}"] = s.planned_weight
        with st.container():
            c = st.columns([0.5, 1.5, 1.5, 1, 1, 1])
            c[0].write(f"#{s.id}")
            c[1].write(f"**{s.planned_weight}** x {s.target_reps}")
            
            act_w = c[2].number_input("W", 0.0, step=5.0, key=f"{session_key}_actual_weight_{i}", label_visibility="collapsed")
            act_r = c[3].number_input("R", int(s.target_reps) if isinstance(s.target_reps, int) else 5, key=f"{session_key}_actual_reps_{i}", label_visibility="collapsed")
            act_rpe = c[4].number_input("RPE", 0.0, step=0.5, key=f"{session_key}_actual_rpe_{i}", label_visibility="collapsed")
            
            e1rm = SetData(s.id, s.planned_weight, s.target_reps, act_w, act_r, act_rpe).get_e1rm()
            if e1rm > 0:
                c[5].markdown(f"**{int(e1rm)}**")
                best_e1rm = max(best_e1rm, e1rm)
            else: c[5].write("-")

    if best_e1rm > 0: st.success(f"🏆 Session Best: {int(best_e1rm)} lbs")
    st.divider()

    # --- SUPPLEMENTAL ---
    st.subheader(f"2️⃣ Supplemental")
    
    c_sel, c_mod_supp = st.columns([1, 1])
    
    # Lift Selector
    all_lifts = LIFT_DB["Squat Pattern"] + LIFT_DB["Bench Pattern"] + LIFT_DB["Deadlift Pattern"] + LIFT_DB["Upper Pull"]
    
    # Try to keep the default aligned with main lift
    try:
        def_idx = all_lifts.index(pivot_base)
    except ValueError:
        def_idx = 0
        
    supp_lift = c_sel.selectbox("Lift", all_lifts, index=def_idx)
    supp_mods = c_mod_supp.multiselect("Modifiers", ALL_MODS, key=f"{session_key}_supp_mods")
    
    supp_full_name = f"{' '.join(supp_mods)} {supp_lift}".strip()
    
    # Calc Target
    supp_tm = st.session_state.user_profile.get_tm(supp_lift)
    if week > 3: supp_tm += (10 if "Bench" not in supp_lift else 5)
    target_w = round((supp_tm * supp_pct) / 5) * 5
    
    st.info(f"**{supp_scheme}** | {supp_full_name} | Target: {target_w} lbs")

    # Logging
    sc = st.columns([1, 1, 1])
    sc[0].markdown("Weight"); sc[1].markdown("Reps"); sc[2].markdown("RPE")
    for j in range(5):
        r = st.columns([1, 1, 1])
        r[0].number_input("W", float(target_w), step=5.0, key=f"{session_key}_supp_w_{j}", label_visibility="collapsed")
        r[1].number_input("R", 5, key=f"{session_key}_supp_r_{j}", label_visibility="collapsed")
        r[2].number_input("RPE", 0.0, step=0.5, key=f"{session_key}_supp_rpe_{j}", label_visibility="collapsed")

    st.divider()

    # --- ACCESSORIES ---
    st.subheader("3️⃣ Accessories")
    if not st.session_state.added_accessories:
        st.info("No accessories added yet. Check Sidebar ➡️")
    
    for idx, acc_name in enumerate(st.session_state.added_accessories):
        st.markdown(f"**{acc_name}**")
        ac = st.columns([1, 1, 1])
        ac[0].caption("Weight"); ac[1].caption("Reps"); ac[2].caption("RPE")
        for k in range(3):
            ar = st.columns([1, 1, 1])
            ar[0].number_input("W", 0.0, step=5.0, key=f"{session_key}_acc_{idx}_w_{k}", label_visibility="collapsed")
            ar[1].number_input("R", 10, step=1, key=f"{session_key}_acc_{idx}_r_{k}", label_visibility="collapsed")
            ar[2].number_input("RPE", 0.0, step=0.5, key=f"{session_key}_acc_{idx}_rpe_{k}", label_visibility="collapsed")
        st.divider()

    if st.button("✅ Finish Workout", type="primary"):
        st.balloons()
        st.success("Workout Saved!")
