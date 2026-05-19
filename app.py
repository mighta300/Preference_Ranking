import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

# --- CONFIGURATION ---
ADMIN_PASSWORD = "admin"  # 👈 Change this to your preferred password!

# --- GLOBAL SHARED DATABASE ---
@st.cache_resource
def get_global_db():
    return {
        "config": {
            "target_votes": 3, 
            "choices": ["Choice A", "Choice B", "Choice C"]
        },
        "votes": {}  # Format: { "Teammate Name": [Rank1, Rank2, Rank3] }
    }

db = get_global_db()

# --- APP LAYOUT ---
st.title("🤝 Automated Team Matcher")
st.write("Teammates can cast their private votes below. Progress updates live.")

tab1, tab2 = st.tabs(["🗳️ Teammate Portal", "⚙️ Admin Setup"])

# --- TAB 1: TEAMMATE PORTAL (Default View) ---
with tab1:
    choices = db["config"]["choices"]
    target_votes = db["config"]["target_votes"]
    current_votes = len(db["votes"])
    
    st.header("Cast Your Private Vote")
    st.info(f"**Progress Live Tracker:** {current_votes} out of {target_votes} teammates have submitted.")
    
    if current_votes < target_votes:
        with st.form("voting_form"):
            name = st.text_input("Your Name:")
            st.write("Rank the items below using the **-** and **+** buttons. **1 is your favorite**, 2 is second favorite, etc.")
            
            user_ranks = []
            # Render step inputs with - / + buttons for each choice independently
            for i, choice in enumerate(choices):
                rank = st.number_input(
                    f"Rank for {choice}:",
                    min_value=1,
                    max_value=len(choices),
                    value=i + 1,  # Sets default sequential ranks (1, 2, 3...) to help avoid accidental ties
                    step=1,
                    key=f"vote_{choice}"
                )
                user_ranks.append(rank)
                
            submitted = st.form_submit_button("Submit Private Vote")
            if submitted:
                if not name:
                    st.error("❌ Please enter your name before submitting.")
                elif name in db["votes"]:
                    st.error("❌ A teammate with this name has already voted!")
                elif len(set(user_ranks)) != len(user_ranks):
                    st.error("❌ Submission Blocked: You assigned the same rank to multiple choices. Please remove any ties!")
                else:
                    db["votes"][name] = user_ranks
                    st.success("Your vote has been recorded privately!")
                    st.rerun()
    else:
        st.success("🎉 All teammates have responded! Calculating the optimal allocation...")

    # --- ALGORITHM & CLEAN RESULTS SECTION ---
    if len(db["votes"]) >= target_votes:
        st.header("🏁 Final Matched Results")
        
        team_members = list(db["votes"].keys())
        cost_matrix = [db["votes"][member] for member in team_members]
        cost_matrix = np.array(cost_matrix)
        
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        match_results = []
        for r, c in zip(row_ind, col_ind):
            if r < len(team_members) and c < len(choices):
                match_results.append({
                    "Teammate": team_members[r],
                    "Assigned Choice": choices[c]
                })
        
        res_df = pd.DataFrame(match_results)
        st.balloons()
        st.dataframe(res_df, use_container_width=True, hide_index=True)

# --- TAB 2: ADMIN SETUP (Protected View) ---
with tab2:
    st.header("🔒 Admin Authentication")
    input_password = st.text_input("Enter Admin Password to modify settings:", type="password")
    
    if input_password == ADMIN_PASSWORD:
        st.success("Access Granted.")
        st.subheader("Configure the Matchmaking Event")
        
        target = st.number_input("How many teammates need to participate?", min_value=1, value=db["config"]["target_votes"])
        choices_raw = st.text_input("Enter the choices/objects (comma-separated):", ", ".join(db["config"]["choices"]))
        
        if st.button("Save & Initialize Page"):
            choices_list = [c.strip() for c in choices_raw.split(",") if c.strip()]
            db["config"] = {"target_votes": target, "choices": choices_list}
            db["votes"] = {} 
            st.success("Page reconfigured globally! Fresh voting session started.")
            st.rerun()
    elif input_password != "":
        st.error("❌ Incorrect Password. Access Denied.")
