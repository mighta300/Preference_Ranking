import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

# --- IN-MEMORY DATABASE SIMULATION ---
# For a live production web app, replace st.session_state with a real database
# like Streamlit's connection to Google Sheets or Supabase.
if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = True
    st.session_state.config = {"target_votes": 3, "choices": ["Choice A", "Choice B", "Choice C"]}
    st.session_state.votes = {}  # Format: { "Teammate Name": [Rank1, Rank2, Rank3] }

# --- APP LAYOUT ---
st.title("🤝 Automated Team Matcher")
st.write("An admin sets it up, teammates vote privately, and results unlock when everyone finishes.")

# Create tabs for Admin Setup and Teammate Portal
tab1, tab2 = st.tabs(["⚙️ Admin Setup", "🗳️ Teammate Portal"])

# --- TAB 1: ADMIN SETUP ---
with tab1:
    st.header("Configure the Matchmaking Event")
    
    target = st.number_input("How many teammates need to participate?", min_value=1, value=st.session_state.config["target_votes"])
    choices_raw = st.text_input("Enter the choices/objects (comma-separated):", ", ".join(st.session_state.config["choices"]))
    
    if st.button("Save & Initialize Page"):
        choices_list = [c.strip() for c in choices_raw.split(",") if c.strip()]
        st.session_state.config = {"target_votes": target, "choices": choices_list}
        st.session_state.votes = {} # Reset votes for new session
        st.success("Page configured successfully! Share your URL with your team.")

# --- TAB 2: TEAMMATE PORTAL ---
with tab2:
    choices = st.session_state.config["choices"]
    target_votes = st.session_state.config["target_votes"]
    current_votes = len(st.session_state.votes)
    
    st.header("Cast Your Private Vote")
    
    # Live Progress Tracker
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
                elif name in st.session_state.votes:
                    st.error("You have already voted!")
                else:
                    st.session_state.votes[name] = user_ranks
                    st.rerun() # Refresh to update the progress counter
    else:
        st.success("🎉 All teammates have responded! Calculating the optimal allocation...")

    # --- ALGORITHM & RESULTS SECTION ---
    # This block only unlocks and executes when current_votes == target_votes
    if len(st.session_state.votes) >= target_votes:
        st.header("🏁 Final Matched Results")
        
        team_members = list(st.session_state.votes.keys())
        
        # Build the cost matrix from preferences
        cost_matrix = []
        for member in team_members:
            cost_matrix.append(st.session_state.votes[member])
        
        cost_matrix = np.array(cost_matrix)
        
        # Run Hungarian Algorithm (Linear Sum Assignment) to maximize total preference satisfaction
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # Format results into a clean table
        match_results = []
        for r, c in zip(row_ind, col_ind):
            # Safe boundary check if choices/team counts are slightly asymmetric
            if r < len(team_members) and c < len(choices):
                match_results.append({
                    "Teammate": team_members[r],
                    "Assigned Choice": choices[c],
                    "Preference Rank": st.session_state.votes[team_members[r]][c]
                })
        
        res_df = pd.DataFrame(match_results)
        st.balloons()
        st.table(res_df)
