import streamlit as st
import pandas as pd
from datetime import datetime, date

# --- CONFIGURATION ---
st.set_page_config(page_title="5/3/1 Tracker", page_icon="🏋️")

# --- 5/3/1 LOGIC & CALCULATOR ---
def calculate_plates(target_weight):
    """Simple plate math for home gym"""
    bar = 45
    if target_weight < bar: return "Just the bar"
    
    remaining = target_weight - bar
    side_weight = remaining / 2
    
    plates = [45, 25, 10, 5, 2.5]
    on_one_side = []
    
    for p in plates:
        while side_weight >= p:
            on_one_side.append(str(p))
            side_weight -= p
            
    return f"Per side: {', '.join(on_one_side)}"

def get_training_max(lift, one_rm):
    return round((one_rm * 0.9) / 5) * 5

# --- APP INTERFACE ---
st.title("5/3/1 Block Manager")

# Sidebar for Settings
with st.sidebar:
    st.header("⚙️ Configuration")
    # Using Session State to store temporary inputs
    sq_max = st.number_input("Squat 1RM", value=465, step=5)
    bp_max = st.number_input("Bench 1RM", value=300, step=5)
    dl_max = st.number_input("Deadlift 1RM", value=560, step=5)
    
    current_week = st.selectbox("Current Week", [1, 2, 3], index=0)
    
    st.markdown("---")
    st.markdown("### 🧮 Plate Calculator")
    calc_weight = st.number_input("Target Weight", value=135, step=5)
    st.caption(calculate_plates(calc_weight))

# --- MAIN WORKOUT VIEW ---
st.subheader(f"Week {current_week} Protocol")

# Define the percentages for the week
if current_week == 1:
    percents = [0.65, 0.75, 0.85]
    reps = [5, 5, "5+"]
elif current_week == 2:
    percents = [0.70, 0.80, 0.90]
    reps = [3, 3, "3+"]
else:
    percents = [0.75, 0.85, 0.95]
    reps = [5, 3, "1+"]

# Tabs for each day
tab1, tab2, tab3 = st.tabs(["Monday (Squat)", "Wednesday (Bench)", "Friday (Deadlift)"])

with tab1:
    tm = get_training_max("Squat", sq_max)
    st.info(f"Training Max: {tm} lbs")
    
    df_squat = pd.DataFrame({
        "Set": [1, 2, 3],
        "%": [f"{int(p*100)}%" for p in percents],
        "Weight": [round((tm * p)/5)*5 for p in percents],
        "Reps": reps,
        "Completed": [False, False, False] # In a real app, this comes from DB
    })
    
    # DataEditor allows you to check boxes like a spreadsheet
    st.data_editor(
        df_squat, 
        column_config={"Completed": st.column_config.CheckboxColumn(required=True)},
        disabled=["Set", "%", "Weight", "Reps"],
        hide_index=True
    )
    
    st.write("### 🏗️ Assistance")
    st.checkbox("First Set Last (5x5)", key="sq_fsl")
    st.checkbox("Accessories (Push/Pull/Core)", key="sq_acc")

with tab2:
    tm = get_training_max("Bench", bp_max)
    st.info(f"Training Max: {tm} lbs")
    
    df_bench = pd.DataFrame({
        "Set": [1, 2, 3],
        "%": [f"{int(p*100)}%" for p in percents],
        "Weight": [round((tm * p)/5)*5 for p in percents],
        "Reps": reps,
        "Completed": [False, False, False]
    })
    
    st.data_editor(
        df_bench, 
        column_config={"Completed": st.column_config.CheckboxColumn(required=True)},
        disabled=["Set", "%", "Weight", "Reps"],
        hide_index=True
    )
    
    st.write("### 🏗️ Assistance")
    st.checkbox("First Set Last (5x5)", key="bp_fsl")
    st.checkbox("Accessories (Push/Pull/Core)", key="bp_acc")

with tab3:
    tm = get_training_max("Deadlift", dl_max)
    st.info(f"Training Max: {tm} lbs")
    
    df_dl = pd.DataFrame({
        "Set": [1, 2, 3],
        "%": [f"{int(p*100)}%" for p in percents],
        "Weight": [round((tm * p)/5)*5 for p in percents],
        "Reps": reps,
        "Completed": [False, False, False]
    })
    
    st.data_editor(
        df_dl, 
        column_config={"Completed": st.column_config.CheckboxColumn(required=True)},
        disabled=["Set", "%", "Weight", "Reps"],
        hide_index=True
    )
    
    st.write("### 🏗️ Assistance")
    st.checkbox("First Set Last (5x5)", key="dl_fsl")
    st.checkbox("Accessories (Push/Pull/Core)", key="dl_acc")

# --- SAVE BUTTON (Placeholder) ---
if st.button("Save Workout Log"):
    st.success("Ideally, this button writes to your Google Sheet!")