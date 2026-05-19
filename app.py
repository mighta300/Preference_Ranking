import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

# --- GLOBAL SHARED DATABASE (Shared across all users/devices) ---
@st.cache_resource
def get_global_db():
    # This dictionary persists on the server memory across all sessions
    return {
        "config": {
            "target_votes": 3, 
            "choices": ["Choice A", "Choice B", "Choice C"]
        },
        "votes": {}  # Format: { "Teammate Name": [Rank1, Rank2, Rank3] }
    }

# Fetch the single global instance of our data
db = get_global_db()

# --- APP LAYOUT ---
st.title("🤝 Automated Team Matcher")
st.write("An admin sets it up, teammates vote privately, and results unlock when everyone finishes.")

# Create tabs for Admin Setup and Teammate Portal
tab1, tab2 = st.tabs(["⚙️ Admin Setup", "🗳️ Teammate Portal"])

# --- TAB 1: ADMIN SETUP ---
with tab1:
    st.header("Configure the Matchmaking Event")
    
    target = st.number_input("How many teammates need to participate?", min_value=1, value=db["config"]["target_votes"])
    choices_raw = st.text_input("Enter the choices/objects (comma-separated):", ", ".join(db["config"]["choices"]))
    
    if st.button("Save & Initialize Page"):
        choices_list = [c.strip() for c in choices_raw.split(",") if c.strip()]
        # Update the global memory directly
        db["config"] = {"target_votes": target, "choices": choices_list}
        db["votes"] = {} # Clear past votes for the new session
        st.success("Page configured globally! You can now share your URL with your team.")
        st.rerun()

# --- TAB 2: TEAMMATE PORTAL ---
with tab2:
    choices = db["config"]["choices"]
    target_votes = db["config"]["target_votes"]
    current_votes = len(db["votes"])
    
    st.header("Cast Your Private Vote")
    
    # Live Progress Tracker (Now updates globally in real-time!)
    st.info(f"**Progress Live Tracker:** {current_votes} out of {target_votes} teammates have submitted.")
    
    # Voting Form (Hidden if group already finished)
    if current_votes < target_votes:
        with st.form("voting_form"):
            name = st.text_input("Your Name:")
            st.write("Rank the following items (**1 is your favorite**, 2 is second favorite, etc.):")
            
            user_ranks = []
            for choice in choices:
                rank = st.number_input(f"Rank for {choice}:", min_value=1, max_value=len(choices), step=1, key=f"vote_{choice}")
                user_ranks.append(rank)
                
            submitted = st.form_submit_button("Submit Private Vote")
            if submitted:
                if not name:
                    st.error("Please enter your name before submitting.")
                elif name in db["votes"]:
                    st.error("A teammate with this name has already voted!")
                else:
                    # Write directly to the global database
                    db["votes"][name] = user_ranks
                    st.success("Your vote has been recorded privately!")
                    st.rerun() # Refresh immediately to update the counter for this user
    else:
        st.success("🎉 All teammates have responded! Calculating the optimal allocation...")

    # --- ALGORITHM & RESULTS SECTION ---
    # Unlocks instantly for everyone once the target is hit
    if len(db["votes"]) >= target_votes:
        st.header("🏁 Final Matched Results")
        
        team_members = list(db["votes"].keys())
        
        # Build the cost matrix from global preferences
        cost_matrix = []
        for member in team_members:
            cost_matrix.append(db["votes"][member])
        
        cost_matrix = np.array(cost_matrix)
        
        # Run Hungarian Algorithm to maximize total satisfaction
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # Format results into a clean table
        match_results = []
        for r, c in zip(row_ind, col_ind):
            if r < len(team_members) and c < len(choices):
                match_results.append({
                    "Teammate": team_members[r],
                    "Assigned Choice": choices[c],
                    "Preference Rank": db["votes"][team_members[r]][c]
                })
        
        res_df = pd.DataFrame(match_results)
        st.balloons()
        st.table(res_df)
