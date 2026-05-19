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

# Initialize session-specific variables to manage the confirmation overlay step
if "confirm_submit" not in st.session_state:
    st.session_state.confirm_submit = False
if "pending_vote" not in st.session_state:
    st.session_state.pending_vote = None
if "pending_name" not in st.session_state:
    st.session_state.pending_name = ""

# --- APP LAYOUT ---
st.title("🤝 Automated Team Matcher")
st.write("Teammates can cast their private votes below. Results will show up when everyone votes.")

# Added a third tab dedicated entirely to the algorithm's explanation
tab1, tab2, tab3 = st.tabs(["🗳️ Teammate Portal", "⚙️ Admin Setup", "ℹ️ How It Works"])

# --- TAB 1: TEAMMATE PORTAL (Default View) ---
with tab1:
    choices = db["config"]["choices"]
    target_votes = db["config"]["target_votes"]
    current_votes = len(db["votes"])
    
    st.header("Cast Your Private Vote")
    st.info(f"**Progress Live Tracker:** {current_votes} out of {target_votes} teammates have submitted.")
    
    if current_votes < target_votes:
        # Step 1: Render the Primary Voting Form
        if not st.session_state.confirm_submit:
            with st.form("voting_form"):
                name = st.text_input("Your Name:")
                st.write("Rank the items below using the **-** and **+** buttons. **1 is your favorite**, 2 is second favorite, etc.")
                
                user_ranks = []
                # Render step inputs with - / + buttons for each choice independently
                for i, choice in enumerate(choices):
                    rank = st.number_input(
                        f"{choice}:",
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
                        # Intercept submission: cache values locally in session_state and flip confirmation flag
                        st.session_state.pending_name = name
                        st.session_state.pending_vote = user_ranks
                        st.session_state.confirm_submit = True
                        st.rerun()
        
        # Step 2: Render the Confirmation Box with Yes/No Buttons
        else:
            st.warning(f"⚠️ **Attention {st.session_state.pending_name}:** Once you submit, your decision is final and cannot be modified. Do you want to proceed?")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Submit", use_container_width=True):
                    # Commit state parameters to the global database instance
                    db["votes"][st.session_state.pending_name] = st.session_state.pending_vote
                    
                    # Flush temporary buffer fields
                    st.session_state.confirm_submit = False
                    st.session_state.pending_name = ""
                    st.session_state.pending_vote = None
                    
                    st.success("Your vote has been recorded privately!")
                    st.rerun()
                    
            with col2:
                if st.button("❌ No, Go Back", use_container_width=True):
                    # Revert back to the initial input form state safely
                    st.session_state.confirm_submit = False
                    st.session_state.pending_name = ""
                    st.session_state.pending_vote = None
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

# --- TAB 3: HOW IT WORKS (Public Educational Explanation) ---
with tab3:
    st.header("⚙️ Intuition")
    
    st.markdown("""
    ### The Hungarian Algorithm (Kuhn-Munkres)
    1. **The Goal:** The algorithm minimizes the global sum of assigned ranks. Since a lower rank means a more preferred item ($1 = \\text{Favorite}$), minimizing this total sum mathematically translates to **maximizing total group satisfaction**.
    2. **Why it's fair:** If Alice and Bob both want *Choice A* as their #1, but Alice absolutely hates *Choice B* (ranks it #3) while Bob doesn't mind it (ranks it #2), the system computes these trade-offs. It allocates *Choice A* to Alice and *Choice B* to Bob because that matrix pair minimizes global disappointment ($1 + 2 = 3$) compared to the reverse ($3 + 1 = 4$).
    3. **Strategy-Proofness:** Because the mechanism actively aims to grant everyone their highest available choice globally, your best strategy is always to report your **true, honest preferences**. Altering your true rankings strategically is highly likely to backfire.
    """)
