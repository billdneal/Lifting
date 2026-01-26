import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional

# ==========================================
# 1. CORE LOGIC (Your Classes)
# ==========================================

# --- Full RTS Table for RPE Calculations ---
# Source: Reactive Training Systems (Approximate values)
RTS_TABLE = {
    10: {1: 1.000, 2: 0.955, 3: 0.922, 4: 0.892, 5: 0.863, 6: 0.837, 7: 0.811, 8: 0.786, 9: 0.762, 10: 0.739},
    9.5: {1: 0.978, 2: 0.939, 3: 0.907, 4: 0.878, 5: 0.850, 6: 0.824, 7: 0.799, 8: 0.774, 9: 0.751, 10: 0.728},
    9:  {1: 0.955, 2: 0.922, 3: 0.892, 4: 0.863, 5: 0.837, 6: 0.811, 7: 0.786, 8: 0.762, 9: 0.739, 10: 0.717},
    8.5: {1: 0.939, 2: 0.907, 3: 0.878, 4: 0.850, 5: 0.824, 6: 0.799, 7: 0.774, 8: 0.751, 9: 0.728, 10: 0.706},
    8:  {1: 0.922, 2: 0.892, 3: 0.863, 4: 0.837, 5: 0.811, 6: 0.786, 7: 0.762, 8: 0.739, 9: 0.717, 10: 0.696},
    7.5: {1: 0.907, 2: 0.878, 3: 0.850, 4: 0.824, 5: 0.799, 6: 0.774, 7: 0.751, 8: 0.728, 9: 0.706, 10: 0.685},
    7:  {1: 0.892, 2: 0.863, 3: 0.837, 4: 0.811, 5: 0.786, 6: 0.762, 7: 0.739, 8: 0.717, 9: 0.696, 10: 0.675},
    6.5: {1: 0.878, 2: 0.850, 3: 0.824, 4: 0.799, 5: 0.774, 6: 0.751, 7: 0.728, 8: 0.706, 9: 0.685, 10: 0.665},
    6:  {1: 0.863, 2: 0.837, 3: 0.811, 4: 0.786, 5: 0.762, 6: 0.739, 7: 0.717, 8: 0.696, 9: 0.675, 10: 0.655}
}

@dataclass
class WorkoutSet:
    exercise: str
    weight: float
    target_reps: int
    actual_reps: Optional[int] = None
    rpe: Optional[float] = None
    completed: bool = False
    
    def calculate_e1rm(self) -> Optional[float]:
        """Calculate e1RM using RTS table"""
        if not self.actual_reps or not self.rpe:
            return None
            
        # Find closest RPE in table (e.g., treat 8.2 as 8.0 or 8.5)
        available_rpes = sorted(RTS_TABLE.keys())
        closest_rpe = min(available_rpes, key=lambda x: abs(x - self.rpe))
        
        if self.actual_reps in RTS_TABLE[closest_rpe]:
            percentage = RTS_TABLE[closest_rpe][self.actual_reps]
            return round(self.weight / percentage / 5) * 5
        return None

class Five31BlockProgram:
    def __init__(self, maxes: Dict[str, float], tm_percent: float = 0.9):
        self.maxes = maxes
        self.tm_percent = tm_percent
        self.training_days = ['mon', 'wed', 'fri'] 
        
    def generate_week(self, week_num: int) -> Dict:
        block_type = self._get_block_type(week_num)
        target_rpe = self._get_target_rpe(week_num)
        
        week_data = {
            'week': week_num,
            'block': block_type,
            'target_rpe': target_rpe,
            'days': {}
        }
        
        for day in self.training_days:
            main_lift = self._get_main_lift_for_day(day)
            week_data['days'][day] = self._generate_day_workout(
                week_num, day, main_lift, block_type, target_rpe
            )
            
        return week_data
    
    def _generate_day_workout(self, week_num: int, day: str, main_lift: str, 
                             block_type: str, target_rpe: Dict) -> Dict:
        main_weights = self._calculate_main_weights(week_num, main_lift, block_type)
        
        workout = {
            'main_lift': main_lift,
            'block': block_type,
            'target_rpe': target_rpe,
            'exercises': [
                {
                    'name': main_lift.title(),
                    'type': 'main',
                    'sets': self._get_main_sets(block_type),
                    'weights': main_weights,
                    'warmup': self._generate_warmup(main_lift, main_weights[0])
                },
                {
                    'name': f'Supplemental {main_lift.title()}',
                    'type': 'supplemental',
                    'sets': '5x5',
                    'weight': main_weights[0]  # FSL weight (First set weight)
                },
                {
                    'name': 'Assistance (Push/Pull/Core)',
                    'type': 'accessory',
                    'sets': '50 reps total',
                    'weight': 'Varied'
                }
            ]
        }
        return workout
    
    def _calculate_main_weights(self, week_num: int, lift: str, block_type: str) -> List[float]:
        tm = self.maxes[lift] * self.tm_percent
        
        # Block-specific TM adjustments
        if block_type == '3s':
            tm += 5 if lift == 'bench' else 10
        elif block_type == 'peak':
            tm += 10 if lift == 'bench' else 20
            
        if block_type == '5s':
            percentages = [0.65, 0.75, 0.85]
        elif block_type == '3s':
            percentages = [0.70, 0.80, 0.90]
        elif block_type == 'peak':
            percentages = [0.75, 0.85, 0.95]
        else: # deload
            percentages = [0.70, 0.75, 0.80]
            
        return [round(tm * p / 5) * 5 for p in percentages]
    
    def _get_block_type(self, week_num: int) -> str:
        if week_num <= 3: return '5s'
        elif week_num <= 6: return '3s'
        elif week_num <= 8: return 'peak'
        else: return 'deload'
    
    def _get_target_rpe(self, week_num: int) -> Dict:
        rpe_targets = {
            1: {'min': 7, 'max': 8, 'desc': '2-3 RIR'},
            2: {'min': 8, 'max': 8, 'desc': '2 RIR'},
            3: {'min': 8, 'max': 9, 'desc': '1-2 RIR'},
            4: {'min': 8, 'max': 8, 'desc': '2 RIR'},
            5: {'min': 8.5, 'max': 9, 'desc': '1 RIR'},
            6: {'min': 9, 'max': 9.5, 'desc': '0-1 RIR'},
            7: {'min': 9, 'max': 9.5, 'desc': '0-1 RIR'},
            8: {'min': 9.5, 'max': 10, 'desc': 'Max Effort'},
            9: {'min': 6, 'max': 7, 'desc': 'Deload'}
        }
        return rpe_targets.get(week_num, {'min': 7, 'max': 8, 'desc': ''})
    
    def _get_main_lift_for_day(self, day: str) -> str:
        return {'mon': 'squat', 'wed': 'bench', 'fri': 'deadlift'}.get(day, 'squat')
    
    def _get_main_sets(self, block_type: str) -> str:
        return {'5s': '5/5/5+', '3s': '3/3/3+', 'peak': '5/3/1+', 'deload': '5/5/5'}.get(block_type, '5/5/5')
    
    def _generate_warmup(self, lift: str, first_work_weight: float) -> List[Dict]:
        warmup_percentages = [0.4, 0.5, 0.6]
        warmup_weights = [round(self.maxes[lift] * p / 5) * 5 for p in warmup_percentages]
        warmup_sets = []
        for i, weight in enumerate(warmup_weights):
            if weight < first_work_weight:
                warmup_sets.append({'weight': weight, 'reps': 5, 'desc': 'Warmup'})
        return warmup_sets

# ==========================================
# 2. STREAMLIT INTERFACE
# ==========================================

st.set_page_config(page_title="5/3/1 Smart Block", page_icon="🧠")

st.title("5/3/1 Smart Block Manager")
st.markdown("Based on 5s/3s/Peak Block Model with RPE integration")

# --- SIDEBAR: Configuration ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.subheader("Current Maxes")
    # Using session state maxes if they exist, else default
    sq = st.number_input("Squat", value=465, step=5)
    bp = st.number_input("Bench", value=300, step=5)
    dl = st.number_input("Deadlift", value=560, step=5)
    
    st.subheader("Program Status")
    week_input = st.number_input("Current Week (1-9)", min_value=1, max_value=9, value=1)
    
    # Initialize the Program
    maxes = {'squat': sq, 'bench': bp, 'deadlift': dl}
    program = Five31BlockProgram(maxes)
    
    st.divider()
    
    # --- RPE CALCULATOR (Uses your WorkoutSet class!) ---
    st.header("🧮 RPE Calculator")
    st.caption("Calculate e1RM from any set")
    
    with st.form("rpe_calc"):
        c_weight = st.number_input("Weight", value=225)
        c_reps = st.number_input("Reps", value=5)
        c_rpe = st.number_input("RPE", value=8.0, step=0.5, min_value=1.0, max_value=10.0)
        
        if st.form_submit_button("Calculate"):
            # Using your class logic here
            test_set = WorkoutSet(exercise="Test", weight=c_weight, target_reps=c_reps, actual_reps=c_reps, rpe=c_rpe)
            result = test_set.calculate_e1rm()
            if result:
                st.success(f"Estimated Max: **{result} lbs**")
            else:
                st.error("Could not calculate (Check inputs)")

# --- MAIN PAGE: Generate the Workout ---
current_week_data = program.generate_week(week_input)
rpe_info = current_week_data['target_rpe']

# Header Info
col1, col2, col3 = st.columns(3)
col1.metric("Week", f"{week_input} / 9")
col2.metric("Block Phase", current_week_data['block'].upper())
col3.metric("Target Intensity", f"RPE {rpe_info['min']}-{rpe_info['max']}")
st.info(f"💡 **Weekly Focus:** {rpe_info['desc']}")

# Display Tabs for Days
tab_mon, tab_wed, tab_fri = st.tabs(["Monday (Squat)", "Wednesday (Bench)", "Friday (Deadlift)"])

def render_day(day_key):
    day_data = current_week_data['days'][day_key]
    main_ex = day_data['exercises'][0] # Main Lift
    supp_ex = day_data['exercises'][1] # Supplemental
    
    st.header(f"{day_data['main_lift'].title()}")
    
    # 1. Warmups
    with st.expander("🔥 Warmup Sets", expanded=True):
        warmup_df = pd.DataFrame(main_ex['warmup'])
        if not warmup_df.empty:
            st.dataframe(warmup_df[['desc', 'weight', 'reps']], hide_index=True, use_container_width=True)
        else:
            st.write("First working set is light enough to start.")

    # 2. Main Work
    st.subheader("🏋️ Main Work")
    st.write(f"**Scheme:** {main_ex['sets']}")
    
    # Create a nice table for the 3 main sets
    main_sets_data = []
    reps_list = main_ex['sets'].split('/')
    
    for i, weight in enumerate(main_ex['weights']):
        # Determine reps for this specific set
        current_reps = reps_list[i] if i < len(reps_list) else reps_list[-1]
        
        main_sets_data.append({
            "Set": i+1,
            "Weight (lbs)": weight,
            "Target Reps": current_reps,
            "RPE Target": f"{rpe_info['min']}-{rpe_info['max']}"
        })
    
    df_main = pd.DataFrame(main_sets_data)
    
    # Editable Dataframe for tracking
    edited_df = st.data_editor(
        df_main,
        column_config={
            "Completed": st.column_config.CheckboxColumn(default=False),
            "Actual Reps": st.column_config.NumberColumn(default=0),
            "Actual RPE": st.column_config.NumberColumn(default=0.0)
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed"
    )

    # 3. Supplemental
    st.subheader("🏗️ Supplemental")
    st.write(f"**{supp_ex['name']}**")
    st.write(f"{supp_ex['sets']} @ {supp_ex['weight']} lbs")
    st.checkbox("Supplemental Completed", key=f"supp_{day_key}")

    # 4. Accessories
    st.subheader("💪 Accessories")
    st.info("50 reps total: Push / Pull / Single-Leg or Core")

# Render the tabs
with tab_mon:
    render_day('mon')
with tab_wed:
    render_day('wed')
with tab_fri:
    render_day('fri')
