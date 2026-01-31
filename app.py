import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🔌 Connection Test")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.write("✅ Connection Object Created")
    
    # Try to read the 'Library' tab
    st.write("⏳ Attempting to read 'Library' tab...")
    df = conn.read(worksheet="Library")
    
    st.success("🎉 Success! Data found:")
    st.dataframe(df)

except Exception as e:
    st.error(f"❌ Failed: {e}")
    st.write("Check your secrets.toml formatting.")
    # This prints exactly what Streamlit sees in your secrets (safe to view only for you)
    st.write("Debug info:")
    st.json(st.secrets)
