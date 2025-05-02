import pandas as pd
import streamlit as st
import requests

# Helper: Convert overs to decimal format (e.g. 49.5 to 49 + 5/6)
def convert_overs(overs):
    if pd.isna(overs):
        return 0
    full_overs = int(overs)
    balls = round((overs - full_overs) * 10)
    return full_overs + balls / 6

# Helper: Split "735/123.1" into (735, 123.1)
def split_runs_overs(col):
    runs = []
    overs = []
    for val in col:
        try:
            run, over = str(val).split("/")
            runs.append(int(run.strip()))
            overs.append(float(over.strip()))
        except:
            runs.append(0)
            overs.append(0.0)
    return runs, overs
st.set_page_config(page_title="Team NRR Calculator", layout="wide")
st.title("🏏 Cricket Points Table - NRR Calculator")

# Load data from CricClubs
url = "https://cricclubs.com/MountainHouseTracyCricketAssociationMTCA/viewPointsTable.do?league=71&year=2025&clubId=14653"
response = requests.get(url)

# Fetch all tables and select the second one
tables = pd.read_html(response.text)
print(f"{len(tables)} tables found")

# Get the second table
df = tables[1]
print(df.head())  # Preview the first few rows

# Clean column names and drop extra header if any
if df.columns.nlevels > 1:
    df.columns = df.columns.get_level_values(-1)
if "Rank" in df.columns:
    df.drop(columns=["Rank"], inplace=True)

# Extract numeric stats from "FOR" and "AGAINST" and drop the original columns
df["Run Scored"], df["Overs Played"] = split_runs_overs(df["FOR"])
df["Runs Given"], df["Overs Bowled"] = split_runs_overs(df["AGAINST"])

# Drop the original 'FOR' and 'AGAINST' columns
df.drop(columns=["FOR", "AGAINST"], inplace=True)

# Initialize session state
if "points_table" not in st.session_state:
    st.session_state.points_table = df.copy()

if "history" not in st.session_state:
    st.session_state.history = []

df = st.session_state.points_table

# Display current data and prompt for update
if "points_table" in st.session_state:
    st.markdown("### 📋 Current Points Table")
    st.dataframe(df)

    team_names = df['TEAM'].tolist()
    colA, colB = st.columns(2)
    team_A = colA.selectbox("Select Team A", team_names, key="team_A")
    team_B = colB.selectbox("Select Team B", [t for t in team_names if t != team_A], key="team_B")

    st.markdown("### 📝 Enter Match Stats")

    col1, col2 = st.columns(2)
    a_runs_scored = col1.number_input(f"{team_A} - Runs Scored", min_value=0, step=1, key="a_rs")
    a_overs_played = col2.number_input(f"{team_A} - Overs Played", min_value=0.0, step=0.1, key="a_op")

    col3, col4 = st.columns(2)
    a_runs_given = col3.number_input(f"{team_B} - Runs Scored", min_value=0, step=1, key="a_rg")
    a_overs_bowled = col4.number_input(f"{team_B} - Overs Played", min_value=0.0, step=0.1, key="a_ob")

    winner = st.selectbox("🏆 Who won the match?", options=[team_A, team_B], key="winner")

    if st.button("Update Points Table & NRR"):
        # Store current state in history for revert functionality
        st.session_state.history.append(df.copy())

        # Increment match counts
        df.loc[df['TEAM'] == team_A, 'MAT'] += 1
        df.loc[df['TEAM'] == team_B, 'MAT'] += 1

        # Update stats for Team A
        idx_A = df[df['TEAM'] == team_A].index[0]
        idx_B = df[df['TEAM'] == team_B].index[0]

        df.at[idx_A, 'Run Scored'] += a_runs_scored
        df.at[idx_A, 'Overs Played'] += a_overs_played
        df.at[idx_A, 'Runs Given'] += a_runs_given
        df.at[idx_A, 'Overs Bowled'] += a_overs_bowled

        # Team B stats derived from Team A
        df.at[idx_B, 'Run Scored'] += a_runs_given
        df.at[idx_B, 'Overs Played'] += a_overs_bowled
        df.at[idx_B, 'Runs Given'] += a_runs_scored
        df.at[idx_B, 'Overs Bowled'] += a_overs_played

        # Update points
        if winner == team_A:
            df.loc[df['TEAM'] == team_A, 'PTS'] += 2
            df.loc[df['TEAM'] == team_B, 'PTS'] += 0
            df.loc[df['TEAM'] == team_A, 'WON'] += 1
            df.loc[df['TEAM'] == team_B, 'LOST'] += 1
        else:
            df.loc[df['TEAM'] == team_B, 'PTS'] += 2
            df.loc[df['TEAM'] == team_A, 'PTS'] += 0
            df.loc[df['TEAM'] == team_B, 'WON'] += 1
            df.loc[df['TEAM'] == team_A, 'LOST'] += 1

        # Recalculate NRR
        df['Adj Overs Played'] = df['Overs Played'].apply(convert_overs)
        df['Adj Overs Bowled'] = df['Overs Bowled'].apply(convert_overs)
        df['Updated NRR'] = (
            df['Run Scored'] / df['Adj Overs Played']
            - df['Runs Given'] / df['Adj Overs Bowled']
        )

        # Store updated DataFrame
        st.session_state.points_table = df

        leaderboard = df.sort_values(by=['PTS', 'Updated NRR'], ascending=[False, False]).reset_index(drop=True)

        st.success("Updated successfully. You can now enter another match.")
        st.markdown("### 📊 Updated Leaderboard")
        #st.dataframe(leaderboard[['TEAM', 'PTS', 'MAT', 'WON', 'LOST', 'Updated NRR']].round(4))
        st.dataframe(leaderboard[['TEAM', 'PTS', 'MAT', 'WON', 'LOST', 'Updated NRR', 'Run Scored', 'Adj Overs Played', 'Runs Given', 'Adj Overs Bowled']].round(4))


    # Revert functionality
    if st.button("Revert Point Table to Previous State") and st.session_state.history:
        # Pop last state from history and revert
        df = st.session_state.history.pop()
        st.session_state.points_table = df

        st.success("Reverted Point Table to Previous State.")
        st.dataframe(df)

