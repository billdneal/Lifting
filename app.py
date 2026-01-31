import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🕵️ Tab Detective")
conn = st.connection("gsheets", type=GSheetsConnection)

tabs_to_test = ["Library", "Logs", "Profile", "Readiness", "Constants"]

for tab in tabs_to_test:
    st.write(f"Testing **'{tab}'**...")
    try:
        # Try to read the specific worksheet
        df = conn.read(worksheet=tab)
        st.success(f"✅ '{tab}' is GOOD! (Found {len(df)} rows)")
    except Exception as e:
        st.error(f"❌ '{tab}' FAILED.")
        st.code(str(e))
        # If it fails, stop trying so we can see the error clearly
        st.stop()

st.balloons()
st.write("🎉 All tabs are perfect. You can switch back to the main app!")
