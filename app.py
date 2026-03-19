from datetime import date, datetime, timedelta, time
from pathlib import Path
import random

import pandas as pd
import streamlit as st
from supabase import create_client


USERS = ["Laurence", "Isabel"]

CATEGORIES = [
    "Work",
    "Study",
    "Exercise",
    "Household",
    "Errand",
    "Social",
    "Relaxing",
    "Other",
]

PHOTO_OPTIONS = {
    "Laurence": ["laurence.jpg", "laurence.jpeg", "laurence.png"],
    "Isabel": ["isabel.jpg", "isabel.jpeg", "isabel.png"],
}

PERSON_COLORS = {
    "Laurence": {
        "start": "#1565c0",
        "end": "#42a5f5",
        "soft": "#e3f2fd",
        "accent": "#bbdefb",
        "sidebar": "#d6ecff",
    },
    "Isabel": {
        "start": "#ef6c00",
        "end": "#ffb74d",
        "soft": "#fff3e0",
        "accent": "#ffe0b2",
        "sidebar": "#fff0db",
    },
}

REWARDS = [
    {"name": "Movie Night", "cost": 40},
    {"name": "Pick Dinner", "cost": 30},
    {"name": "Extra Screen Time", "cost": 25},
    {"name": "Sweet Treat", "cost": 20},
    {"name": "Stay Up 15 Minutes Later", "cost": 35},
]

DAILY_CHALLENGES = [
    "Read for 10 minutes",
    "Help tidy one room",
    "Drink water 3 times",
    "Put away your things",
    "Do one kind thing for someone",
]


@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def find_photo(person):
    for filename in PHOTO_OPTIONS.get(person, []):
        if Path(filename).exists():
            return filename
    return None


def add_entry(person, entry_date, entry_time, activity, category, notes, points, mood, challenge_completed):
    supabase = get_supabase()
    supabase.table("entries").insert(
        {
            "person": person,
            "entry_date": entry_date.isoformat(),
            "entry_time": entry_time.strftime("%H:%M"),
            "activity": activity.strip(),
            "category": category,
            "notes": notes.strip(),
            "completed": False,
            "created_at": datetime.utcnow().isoformat(),
            "points": points,
            "mood": mood,
            "challenge_completed": challenge_completed,
        }
    ).execute()


def mark_entry_complete(entry_id):
    supabase = get_supabase()
    supabase.table("entries").update({"completed": True}).eq("id", entry_id).execute()


def get_entries_for_day(selected_date, person=None):
    supabase = get_supabase()
    query = supabase.table("entries").select("*").eq("entry_date", selected_date.isoformat())

    if person:
        query = query.eq("person", person)

    response = query.order("entry_time").execute()
    return response.data


def get_entries_for_week(start_date, end_date, person=None):
    supabase = get_supabase()
    query = (
        supabase.table("entries")
        .select("*")
        .gte("entry_date", start_date.isoformat())
        .lte("entry_date", end_date.isoformat())
    )

    if person:
        query = query.eq("person", person)

    response = query.order("entry_date").order("entry_time").execute()
    return response.data


def get_all_entries(person=None):
    supabase = get_supabase()
    query = supabase.table("entries").select("*").order("entry_date", desc=True).order("entry_time", desc=True)

    if person:
        query = query.eq("person", person)

    response = query.execute()
    return response.data


def get_total_points(person):
    supabase = get_supabase()
    response = supabase.table("entries").select("*").eq("person", person).eq("completed", True).execute()
    rows = response.data

    if not rows:
        return 0

    return int(sum(row.get("points", 0) for row in rows))


def get_weekly_summary(start_date, end_date):
    rows = get_entries_for_week(start_date, end_date)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    summary = (
        df.groupby("person")
        .agg(
            total_entries=("id", "count"),
            completed_entries=("completed", "sum"),
            total_points=("points", "sum"),
        )
        .reset_index()
    )

    summary["completed_entries"] = summary["completed_entries"].astype(int)
    summary["remaining_entries"] = summary["total_entries"] - summary["completed_entries"]
    return summary


def get_badges(person):
    rows = get_all_entries(person)

    if not rows:
        return []

    df = pd.DataFrame(rows)
    completed_df = df[df["completed"] == True]

    badges = []

    if len(completed_df) >= 3:
        badges.append("Busy Bee")
    if len(completed_df) >= 5:
        badges.append("Super Star")
    if len(completed_df[completed_df["category"] == "Study"]) >= 3:
        badges.append("Homework Hero")
    if len(completed_df[completed_df["category"] == "Household"]) >= 3:
        badges.append("Helpful Helper")
    if len(completed_df[completed_df["category"] == "Exercise"]) >= 3:
        badges.append("Fitness Champ")

    return badges


def request_reward(person, reward_name, cost):
    supabase = get_supabase()
    supabase.table("rewards").insert(
        {
            "person": person,
            "reward_name": reward_name,
            "cost": cost,
            "approved": False,
            "created_at": datetime.utcnow().isoformat(),
        }
    ).execute()


def get_rewards(person=None):
    supabase = get_supabase()
    query = supabase.table("rewards").select("*").order("created_at", desc=True)

    if person:
        query = query.eq("person", person)

    response = query.execute()
    return response.data


def approve_reward(reward_id):
    supabase = get_supabase()
    supabase.table("rewards").update({"approved": True}).eq("id", reward_id).execute()


def is_parent_logged_in():
    return st.session_state.get("parent_logged_in", False)


st.set_page_config(page_title="Kids Tracker", page_icon="🌟", layout="wide")

selected_user = st.sidebar.selectbox("Choose a person", USERS)
page = st.sidebar.radio("Go to", ["Today", "Profile", "Rewards", "Games", "Parent Zone"])
colors = PERSON_COLORS[selected_user]

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(135deg, {colors["soft"]} 0%, #ffffff 50%, {colors["accent"]} 100%);
    }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {colors["sidebar"]} 0%, #ffffff 100%);
    }}

    .block-container {{
        max-width: 1150px;
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }}

    .hero {{
        background: linear-gradient(135deg, {colors["start"]}, {colors["end"]});
        color: white;
        border-radius: 28px;
        padding: 28px;
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.14);
        margin-bottom: 22px;
    }}

    .hero-title {{
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
    }}

    .hero-copy {{
        font-size: 1.05rem;
        margin-top: 10px;
    }}

    .card {{
        background: rgba(255,255,255,0.92);
        border-radius: 24px;
        padding: 22px;
        box-shadow: 0 10px 26px rgba(0, 0, 0, 0.08);
        margin-bottom: 20px;
        border: 1px solid rgba(0,0,0,0.04);
    }}

    .reward-card {{
        background: linear-gradient(180deg, #ffffff 0%, {colors["soft"]} 100%);
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.07);
        margin-bottom: 16px;
    }}

    .mini-title {{
        font-size: 1.35rem;
        font-weight: 800;
        color: #203047;
        margin-bottom: 10px;
    }}

    .chip {{
        display: inline-block;
        background: linear-gradient(135deg, {colors["start"]}, {colors["end"]});
        color: white;
        padding: 7px 12px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 12px;
    }}

    .stButton > button {{
        border: none;
        border-radius: 14px;
        padding: 0.7rem 1.1rem;
        font-weight: 700;
        background: linear-gradient(135deg, {colors["start"]}, {colors["end"]});
        color: white;
    }}

    .stButton > button:hover {{
        color: white;
        filter: brightness(0.97);
    }}

    .stTextInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input,
    div[data-baseweb="select"] > div {{
        border-radius: 14px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.divider()
st.sidebar.subheader("Parent Login")

password_input = st.sidebar.text_input("Parent password", type="password")

if st.sidebar.button("Login"):
    if password_input == st.secrets["PARENT_PASSWORD"]:
        st.session_state["parent_logged_in"] = True
        st.sidebar.success("Parent access enabled")
    else:
        st.sidebar.error("Wrong password")

if is_parent_logged_in():
    if st.sidebar.button("Logout"):
        st.session_state["parent_logged_in"] = False
        st.rerun()

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">Kids Activity World</div>
        <div class="hero-copy">{selected_user}'s colourful tracker, reward space, and fun zone.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

today = date.today()
week_start = today - timedelta(days=today.weekday())
week_end = week_start + timedelta(days=6)

if "daily_challenge" not in st.session_state:
    st.session_state["daily_challenge"] = random.choice(DAILY_CHALLENGES)

if page == "Today":
    left, right = st.columns([1.1, 2])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        photo_file = find_photo(selected_user)
        if photo_file:
            st.image(photo_file, width=240)
        else:
            st.info(f"Upload a photo for {selected_user}")
        st.markdown(f"### {selected_user}")
        st.markdown(f"**Total points:** {get_total_points(selected_user)}")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Add Today\'s Activity</div>', unsafe_allow_html=True)

        with st.form("add_entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                entry_date = st.date_input("Date", value=today)
                activity = st.text_input("Activity")
                category = st.selectbox("Category", CATEGORIES)
                mood = st.selectbox("Mood", ["Happy", "Excited", "Okay", "Tired"])

            with col2:
                entry_time = st.time_input("Time", value=time(9, 0))
                person = st.selectbox("Person", USERS, index=USERS.index(selected_user))
                points = st.selectbox("Points", [5, 10, 15, 20], index=1)
                notes = st.text_area("Notes")

            challenge_completed = st.checkbox(
                f"Bonus challenge done: {st.session_state['daily_challenge']}"
            )

            submitted = st.form_submit_button("Save entry")

            if submitted:
                if not activity.strip():
                    st.error("Please enter an activity.")
                else:
                    add_entry(
                        person,
                        entry_date,
                        entry_time,
                        activity,
                        category,
                        notes,
                        points,
                        mood,
                        challenge_completed,
                    )
                    st.success("Entry saved.")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="mini-title">Daily Challenge</div>', unsafe_allow_html=True)
    st.info(st.session_state["daily_challenge"])
    st.markdown("</div>", unsafe_allow_html=True)

    today_entries = get_entries_for_day(today, selected_user)
    completed_today = len([entry for entry in today_entries if entry["completed"]])
    total_today = len(today_entries)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="mini-title">Today\'s Progress</div>', unsafe_allow_html=True)

    if total_today > 0:
        progress_value = completed_today / total_today
        st.progress(progress_value)
        st.write(f"{completed_today} of {total_today} tasks completed")
        if completed_today == total_today:
            st.balloons()
            st.success("Amazing job. Everything is done for today.")
    else:
        st.info("No tasks added yet for today.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="mini-title">Today\'s Entries</div>', unsafe_allow_html=True)

    if not today_entries:
        st.info("No entries yet for today.")
    else:
        for entry in today_entries:
            left_col, right_col = st.columns([5, 1])

            with left_col:
                with st.container(border=True):
                    st.markdown(f'<div class="chip">{entry["category"]}</div>', unsafe_allow_html=True)
                    st.markdown(f"**{entry['entry_time']} | {entry['activity']}**")
                    st.write(f"Mood: {entry.get('mood', 'Not set')}")
                    st.write(f"Points: {entry.get('points', 0)}")
                    if entry["notes"]:
                        st.write(entry["notes"])

            with right_col:
                if entry["completed"]:
                    st.success("Done")
                else:
                    if st.button("Complete", key=f"complete_{entry['id']}"):
                        mark_entry_complete(entry["id"])
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Profile":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="mini-title">{selected_user}\'s Profile</div>', unsafe_allow_html=True)

    photo_file = find_photo(selected_user)
    if photo_file:
        st.image(photo_file, width=220)

    total_points = get_total_points(selected_user)
    badges = get_badges(selected_user)
    weekly_entries = get_entries_for_week(week_start, week_end, selected_user)
    completed_week = len([entry for entry in weekly_entries if entry["completed"]])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Points", total_points)
    col2.metric("Completed This Week", completed_week)
    col3.metric("Badges Earned", len(badges))

    st.subheader("Badges")
    if badges:
        for badge in badges:
            st.success(badge)
    else:
        st.info("No badges yet. Complete tasks to earn them.")

    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Rewards":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="mini-title">Rewards Shop</div>', unsafe_allow_html=True)

    total_points = get_total_points(selected_user)
    st.write(f"Available points for {selected_user}: **{total_points}**")

    for reward in REWARDS:
        st.markdown('<div class="reward-card">', unsafe_allow_html=True)
        st.markdown(f"### {reward['name']}")
        st.write(f"Cost: {reward['cost']} points")

        if total_points >= reward["cost"]:
            if st.button(f"Request {reward['name']}", key=f"reward_{reward['name']}"):
                request_reward(selected_user, reward["name"], reward["cost"])
                st.success("Reward requested.")
        else:
            st.caption("Not enough points yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Requested Rewards")
    reward_rows = get_rewards(selected_user)

    if reward_rows:
        for reward in reward_rows:
            status = "Approved" if reward["approved"] else "Waiting for parent approval"
            st.write(f"{reward['reward_name']} - {status}")
    else:
        st.info("No rewards requested yet.")

    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Games":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="mini-title">Fun Zone</div>', unsafe_allow_html=True)
    st.write("Here are some fun mini activities.")

    game_choice = st.selectbox(
        "Choose a fun activity",
        ["Spin the Challenge Wheel", "Lucky Number", "Reaction Game"],
    )

    if game_choice == "Spin the Challenge Wheel":
        if st.button("Spin"):
            st.success(random.choice(DAILY_CHALLENGES))

    elif game_choice == "Lucky Number":
        if st.button("Pick a lucky number"):
            st.success(f"Your lucky number is {random.randint(1, 20)}")

    elif game_choice == "Reaction Game":
        if st.button("Tap for a surprise"):
            messages = ["Boom!", "Super fast!", "Champion!", "You win!", "Star player!"]
            st.success(random.choice(messages))

    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Parent Zone":
    if not is_parent_logged_in():
        st.warning("Parent login required.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Weekly Summary</div>', unsafe_allow_html=True)

        weekly_summary = get_weekly_summary(week_start, week_end)

        if weekly_summary.empty:
            st.info("No entries this week.")
        else:
            st.dataframe(
                weekly_summary.rename(
                    columns={
                        "person": "Person",
                        "total_entries": "Total Entries",
                        "completed_entries": "Completed",
                        "remaining_entries": "Remaining",
                        "total_points": "Points",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Reward Approvals</div>', unsafe_allow_html=True)

        all_rewards = get_rewards()

        pending_rewards = [reward for reward in all_rewards if not reward["approved"]]

        if pending_rewards:
            for reward in pending_rewards:
                st.write(f"{reward['person']} requested {reward['reward_name']} ({reward['cost']} points)")
                if st.button(f"Approve reward {reward['id']}", key=f"approve_{reward['id']}"):
                    approve_reward(reward["id"])
                    st.success("Reward approved.")
                    st.rerun()
        else:
            st.info("No pending reward requests.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">All Entries</div>', unsafe_allow_html=True)

        all_entries = get_all_entries()

        if all_entries:
            df = pd.DataFrame(all_entries)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No entries yet.")

        st.markdown("</div>", unsafe_allow_html=True)

