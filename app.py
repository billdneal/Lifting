import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🔌 Connection Test Phase 2")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.write("✅ Connection Object Created")
    
    # READ DEFAULT (No worksheet name specified = Reads the first tab)
    st.write("⏳ Attempting to read the FIRST tab (whatever it is)...")
    df = conn.read() 
    
    st.success("🎉 Success! Found data in the first tab:")
    st.dataframe(df)

except Exception as e:
    st.error(f"❌ Failed: {e}")
