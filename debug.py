import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🔌 Connection Test")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.write("✅ Connection Object Created")
    
    # Try to read just one tab (Library)
    st.write("⏳ Attempting to read 'Library' tab...")
    df = conn.read(worksheet="Library")
    
    st.success("🎉 Success! Data found:")
    st.dataframe(df)

except Exception as e:
    st.error(f"❌ Failed: {e}")
    st.write("Check your secrets.toml formatting.")
    st.code(st.secrets.to_dict()) # This helps debug what Streamlit actually sees
