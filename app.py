from datetime import date, datetime, timedelta, time
from pathlib import Path
import random
from urllib.parse import quote

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

CATEGORY_ICONS = {
    "Work": "💼",
    "Study": "📚",
    "Exercise": "⚽",
    "Household": "🏠",
    "Errand": "🛍️",
    "Social": "🎉",
    "Relaxing": "🌈",
    "Other": "✨",
}

CATEGORY_POINTS = {
    "Work": 10,
    "Study": 15,
    "Exercise": 15,
    "Household": 20,
    "Errand": 10,
    "Social": 10,
    "Relaxing": 5,
    "Other": 10,
}

PHOTO_OPTIONS = {
    "Laurence": ["laurence.jpg", "laurence.jpeg", "laurence.png"],
    "Isabel": ["isabel.jpg", "isabel.jpeg", "isabel.png"],
}

PERSON_COLORS = {
    "Laurence": {
        "primary": "#00C2FF",
        "secondary": "#007CF0",
        "accent": "#9DFF00",
        "soft": "#EAFBFF",
        "text": "#0D1B2A",
        "sidebar_bg": "#A7F3FF",
        "sidebar_bg_2": "#D8FF7A",
        "sidebar_text": "#0B132B",
    },
    "Isabel": {
        "primary": "#FF4D8D",
        "secondary": "#FF7A00",
        "accent": "#FFD60A",
        "soft": "#FFF1F7",
        "text": "#241623",
        "sidebar_bg": "#FFB3D1",
        "sidebar_bg_2": "#FFE680",
        "sidebar_text": "#381220",
    },
}

REWARDS = [
    {"name": "Movie Night", "cost": 40, "icon": "🎬"},
    {"name": "Pick Dinner", "cost": 30, "icon": "🍕"},
    {"name": "Extra Screen Time", "cost": 25, "icon": "🕹️"},
    {"name": "Sweet Treat", "cost": 20, "icon": "🍭"},
    {"name": "Stay Up 15 Mins Later", "cost": 35, "icon": "🌙"},
]

DAILY_CHALLENGES = [
    "Read for 10 minutes",
    "Help tidy one room",
    "Drink water 3 times",
    "Put away your things",
    "Do one kind thing for someone",
    "Practice something for 15 minutes",
]

PARENT_WHATSAPP_NUMBER = "353858261692"


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def find_photo(person):
    for filename in PHOTO_OPTIONS.get(person, []):
        if Path(filename).exists():
            return filename
    return None


def build_whatsapp_link(person):
    message = (
        f"Hi, this is {person} from Mission Arcade. "
        f"I need help or want to send a message."
    )
    return f"https://wa.me/{PARENT_WHATSAPP_NUMBER}?text={quote(message)}"


def add_entry(person, entry_date, entry_time, activity, category, notes, points, mood, challenge_completed):
    get_supabase().table("entries").insert(
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
    get_supabase().table("entries").update({"completed": True}).eq("id", entry_id).execute()


def get_entries_for_day(selected_date, person=None):
    query = get_supabase().table("entries").select("*").eq("entry_date", selected_date.isoformat())
    if person:
        query = query.eq("person", person)
    return query.order("entry_time").execute().data


def get_entries_for_week(start_date, end_date, person=None):
    query = (
        get_supabase()
        .table("entries")
        .select("*")
        .gte("entry_date", start_date.isoformat())
        .lte("entry_date", end_date.isoformat())
    )
    if person:
        query = query.eq("person", person)
    return query.order("entry_date").order("entry_time").execute().data


def get_all_entries():
    return (
        get_supabase()
        .table("entries")
        .select("*")
        .order("entry_date", desc=True)
        .order("entry_time", desc=True)
        .execute()
        .data
    )


def get_total_points(person):
    rows = (
        get_supabase()
        .table("entries")
        .select("*")
        .eq("person", person)
        .eq("completed", True)
        .execute()
        .data
    )
    return int(sum(row.get("points", 0) for row in rows)) if rows else 0


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
    summary["completion_rate"] = (
        (summary["completed_entries"] / summary["total_entries"]) * 100
    ).round(0).astype(int)
    return summary


def get_badges(person):
    rows = (
        get_supabase()
        .table("entries")
        .select("*")
        .eq("person", person)
        .eq("completed", True)
        .execute()
        .data
    )
    if not rows:
        return []

    df = pd.DataFrame(rows)
    badges = []

    if len(df) >= 3:
        badges.append("Starter")
    if len(df) >= 5:
        badges.append("On Fire")
    if len(df[df["category"] == "Study"]) >= 3:
        badges.append("Brain Boss")
    if len(df[df["category"] == "Exercise"]) >= 3:
        badges.append("Speed Boost")
    if len(df[df["category"] == "Household"]) >= 3:
        badges.append("Helper Hero")
    if "challenge_completed" in df.columns and len(df[df["challenge_completed"] == True]) >= 2:
        badges.append("Challenge Champ")

    return badges


def request_reward(person, reward_name, cost):
    get_supabase().table("rewards").insert(
        {
            "person": person,
            "reward_name": reward_name,
            "cost": cost,
            "approved": False,
            "created_at": datetime.utcnow().isoformat(),
        }
    ).execute()


def get_rewards(person=None):
    query = get_supabase().table("rewards").select("*").order("created_at", desc=True)
    if person:
        query = query.eq("person", person)
    return query.execute().data


def approve_reward(reward_id):
    get_supabase().table("rewards").update({"approved": True}).eq("id", reward_id).execute()


def is_parent_logged_in():
    return st.session_state.get("parent_logged_in", False)


def reset_treasure_game():
    st.session_state["treasure_index"] = random.randint(0, 8)
    st.session_state["treasure_found"] = False
    st.session_state["treasure_revealed"] = []
    st.session_state["treasure_message"] = "Pick a tile and try to find the star."


def play_treasure(position):
    if st.session_state["treasure_found"]:
        return
    revealed = st.session_state["treasure_revealed"]
    if position in revealed:
        return
    revealed.append(position)
    if position == st.session_state["treasure_index"]:
        st.session_state["treasure_found"] = True
        st.session_state["treasure_message"] = "You found the hidden star."
    else:
        st.session_state["treasure_message"] = "Not there. Try another tile."


def reset_lucky_game():
    st.session_state["lucky_target"] = random.randint(1, 10)
    st.session_state["lucky_attempts"] = 0
    st.session_state["lucky_message"] = "Guess the hidden number from 1 to 10."


def submit_lucky_guess(guess):
    target = st.session_state["lucky_target"]
    st.session_state["lucky_attempts"] += 1

    if guess == target:
        st.session_state["lucky_message"] = f"Correct. The number was {target}."
    elif guess < target:
        st.session_state["lucky_message"] = "Too low. Try higher."
    else:
        st.session_state["lucky_message"] = "Too high. Try lower."


def reset_memory_game():
    sequence = [random.randint(1, 4) for _ in range(4)]
    st.session_state["memory_sequence"] = sequence
    st.session_state["memory_message"] = "Memorise the pattern, then type it in with commas."


def check_memory_game(user_input):
    raw = [part.strip() for part in user_input.split(",") if part.strip()]
    try:
        guess = [int(part) for part in raw]
    except ValueError:
        st.session_state["memory_message"] = "Use numbers only, like 1,2,3,4"
        return

    if guess == st.session_state["memory_sequence"]:
        st.session_state["memory_message"] = "Perfect memory."
    else:
        correct = ",".join(str(x) for x in st.session_state["memory_sequence"])
        st.session_state["memory_message"] = f"Not quite. The pattern was {correct}"


def init_game_state():
    if "daily_challenge" not in st.session_state:
        st.session_state["daily_challenge"] = random.choice(DAILY_CHALLENGES)
    if "treasure_index" not in st.session_state:
        reset_treasure_game()
    if "lucky_target" not in st.session_state:
        reset_lucky_game()
    if "memory_sequence" not in st.session_state:
        reset_memory_game()


def render_styles(colors):
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Manrope:wght@400;600;700;800&display=swap');

        .stApp {{
            background:
                radial-gradient(circle at 12% 10%, {colors["accent"]}25 0%, transparent 18%),
                radial-gradient(circle at 88% 18%, {colors["primary"]}22 0%, transparent 16%),
                linear-gradient(180deg, #0B1020 0%, #111827 100%);
            color: white;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {colors["sidebar_bg"]} 0%, {colors["sidebar_bg_2"]} 100%);
            border-right: 1px solid rgba(0,0,0,0.08);
        }}

        section[data-testid="stSidebar"] * {{
            color: {colors["sidebar_text"]} !important;
            font-family: "Sora", sans-serif !important;
        }}

        .block-container {{
            max-width: 1180px;
            padding-top: 1.35rem;
            padding-bottom: 2rem;
        }}

        .hero {{
            background: linear-gradient(135deg, {colors["primary"]}, {colors["secondary"]} 58%, {colors["accent"]});
            border-radius: 34px;
            padding: 34px;
            box-shadow: 0 24px 56px rgba(0,0,0,0.30);
            position: relative;
            overflow: hidden;
            margin-bottom: 18px;
        }}

        .hero:after {{
            content: "";
            position: absolute;
            right: -34px;
            top: -34px;
            width: 180px;
            height: 180px;
            border-radius: 50%;
            background: rgba(255,255,255,0.12);
        }}

        .hero-kicker {{
            font: 800 0.82rem "Sora", sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            opacity: 0.92;
        }}

        .hero-title {{
            font-family: "Sora", sans-serif;
            font-size: 3.1rem;
            font-weight: 800;
            line-height: 1;
            margin-top: 8px;
        }}

        .hero-copy {{
            margin-top: 10px;
            max-width: 720px;
            font-size: 1rem;
            color: rgba(255,255,255,0.92);
            font-family: "Manrope", sans-serif;
        }}

        .card {{
            background: linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.06) 100%);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 28px;
            padding: 20px;
            box-shadow: 0 14px 34px rgba(0,0,0,0.18);
            backdrop-filter: blur(12px);
            margin-bottom: 18px;
        }}

        .section-title {{
            font-family: "Sora", sans-serif;
            font-size: 1.55rem;
            font-weight: 800;
            margin-bottom: 4px;
            color: white;
        }}

        .section-copy {{
            color: rgba(255,255,255,0.72);
            margin-bottom: 14px;
            font-family: "Manrope", sans-serif;
        }}

        .stat-card {{
            border-radius: 26px;
            padding: 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.06) 100%);
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow: 0 12px 28px rgba(0,0,0,0.18);
        }}

        .stat-label {{
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: rgba(255,255,255,0.65);
            font-family: "Sora", sans-serif;
        }}

        .stat-value {{
            font-family: "Sora", sans-serif;
            font-size: 2.1rem;
            margin-top: 6px;
            color: white;
        }}

        .stat-sub {{
            color: rgba(255,255,255,0.72);
            margin-top: 4px;
            font-size: 0.92rem;
        }}

        .entry-grid-card {{
            background: linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.04) 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 16px;
            min-height: 212px;
            margin-bottom: 14px;
        }}

        .chip {{
            display: inline-block;
            border-radius: 999px;
            padding: 7px 12px;
            font-size: 0.8rem;
            font-weight: 800;
            margin-right: 8px;
            margin-bottom: 8px;
            font-family: "Sora", sans-serif;
        }}

        .chip-time {{
            background: rgba(255,255,255,0.12);
            color: white;
        }}

        .chip-category {{
            background: linear-gradient(135deg, {colors["primary"]}, {colors["secondary"]});
            color: white;
        }}

        .chip-done {{
            background: rgba(100,255,140,0.18);
            color: #9DFFB2;
        }}

        .chip-open {{
            background: rgba(255,214,10,0.18);
            color: #FFE16C;
        }}

        .reward-tile {{
            background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.05) 100%);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 22px;
            padding: 16px;
            margin-bottom: 14px;
        }}

        .badge {{
            display: inline-block;
            background: linear-gradient(135deg, {colors["accent"]}, {colors["primary"]});
            color: #0B1020;
            border-radius: 999px;
            padding: 8px 12px;
            margin: 6px 8px 0 0;
            font-weight: 800;
            font-family: "Sora", sans-serif;
        }}

        .photo-wrap img {{
            border-radius: 24px !important;
            box-shadow: 0 18px 34px rgba(0,0,0,0.24);
        }}

        .stButton > button {{
            border: 0;
            border-radius: 16px;
            background: linear-gradient(135deg, {colors["primary"]}, {colors["secondary"]});
            color: white;
            font-weight: 800;
            box-shadow: 0 10px 22px rgba(0,0,0,0.22);
            padding: 0.72rem 1rem;
            font-family: "Sora", sans-serif;
        }}

        .stButton > button:hover {{
            color: white;
            filter: brightness(0.98);
        }}

        .stTextInput input,
        .stTextArea textarea,
        .stDateInput input,
        .stTimeInput input,
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {{
            background: rgba(255,255,255,0.96) !important;
            color: #111827 !important;
            border-radius: 16px !important;
            border: 2px solid transparent !important;
        }}

        div[data-testid="stDataFrame"] {{
            border-radius: 20px;
            overflow: hidden;
        }}

        [data-testid="stAlert"] {{
            border-radius: 18px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label, value, subtext):
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="Mission Arcade", page_icon="🚀", layout="wide")

selected_user = st.sidebar.selectbox("Choose a player", USERS)
page = st.sidebar.radio("Go to", ["Today", "Profile", "Rewards", "Games", "Parent Zone"])
colors = PERSON_COLORS[selected_user]
render_styles(colors)
init_game_state()

st.sidebar.markdown("### Mission Control")
st.sidebar.write("Pick a player and jump into their arcade board.")
st.sidebar.link_button("Chat to Parent", build_whatsapp_link(selected_user))
st.sidebar.divider()
st.sidebar.subheader("Parent Login")

password_input = st.sidebar.text_input("Parent password", type="password")

if st.sidebar.button("Login"):
    if password_input == st.secrets["PARENT_PASSWORD"]:
        st.session_state["parent_logged_in"] = True
        st.sidebar.success("Parent access enabled")
    else:
        st.sidebar.error("Wrong password")

if is_parent_logged_in() and st.sidebar.button("Logout"):
    st.session_state["parent_logged_in"] = False
    st.rerun()

today = date.today()
week_start = today - timedelta(days=today.weekday())
week_end = week_start + timedelta(days=6)

today_entries = get_entries_for_day(today, selected_user)
done_today = len([x for x in today_entries if x["completed"]])
total_today = len(today_entries)
completion_rate = int((done_today / total_today) * 100) if total_today else 0

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">Mission Arcade</div>
        <div class="hero-title">{selected_user}'s Control Deck</div>
        <div class="hero-copy">Bright, modern, game-like, and built around daily wins. Complete missions, collect points, unlock rewards.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

top_1, top_2, top_3 = st.columns(3)
with top_1:
    stat_card("Today", total_today, "missions loaded")
with top_2:
    stat_card("Completed", done_today, "wins secured")
with top_3:
    stat_card("Points", get_total_points(selected_user), "total earned")

if page == "Today":
    left, right = st.columns([1.02, 1.98], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Player Card</div>', unsafe_allow_html=True)
        photo = find_photo(selected_user)
        if photo:
            st.markdown('<div class="photo-wrap">', unsafe_allow_html=True)
            st.image(photo, width=240)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(f"Upload {selected_user.lower()}.jpg or .png")
        st.write(f"**Current challenge:** {st.session_state['daily_challenge']}")
        st.progress(completion_rate / 100 if total_today else 0.0)
        st.write(f"Progress: {done_today} of {total_today} done")
        if total_today and done_today == total_today:
            st.balloons()
            st.success("Mission complete.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Add Mission</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Make the next activity part of today\'s board.</div>', unsafe_allow_html=True)

        with st.form("add_entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                entry_date = st.date_input("Date", value=today)
                activity = st.text_input("Activity", placeholder="Homework, football, reading...")
                category = st.selectbox("Category", CATEGORIES)
                mood = st.selectbox("Mood", ["Happy", "Excited", "Okay", "Tired"])

            points = CATEGORY_POINTS[category]

            with col2:
                entry_time = st.time_input("Time", value=time(9, 0))
                person = st.selectbox("Person", USERS, index=USERS.index(selected_user))
                notes = st.text_area("Notes", placeholder="Optional notes")

            st.caption(f"Points for this activity: {points}")
            challenge_completed = st.checkbox("This mission completes today's bonus challenge")

            submitted = st.form_submit_button("Launch Mission")

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
                    st.success("Mission added.")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Today\'s Missions</div>', unsafe_allow_html=True)

    if not today_entries:
        st.info("No missions yet for today.")
    else:
        rows = [today_entries[index:index + 2] for index in range(0, len(today_entries), 2)]
        for row_index, row_entries in enumerate(rows):
            row_cols = st.columns(2, gap="medium")
            for col_index, entry in enumerate(row_entries):
                with row_cols[col_index]:
                    status_class = "chip-done" if entry["completed"] else "chip-open"
                    status_label = "Done" if entry["completed"] else "Live"
                    st.markdown(
                        f"""
                        <div class="entry-grid-card">
                            <span class="chip chip-time">{entry["entry_time"]}</span>
                            <span class="chip chip-category">{CATEGORY_ICONS.get(entry["category"], "✨")} {entry["category"]}</span>
                            <span class="chip {status_class}">{status_label}</span>
                            <div style="font-size:1.1rem;font-weight:800;margin-top:6px;">{entry["activity"]}</div>
                            <div style="color:rgba(255,255,255,0.72);margin-top:6px;">Mood: {entry.get("mood", "Not set")} | Points: {entry.get("points", 0)}</div>
                            <div style="color:rgba(255,255,255,0.68);margin-top:6px;">{entry["notes"] or "No extra notes."}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if not entry["completed"] and st.button(
                        "Mark Complete",
                        key=f'complete_{entry["id"]}_{row_index}_{col_index}',
                    ):
                        mark_entry_complete(entry["id"])
                        st.rerun()
        if len(rows[-1]) == 1:
            row_cols[1].empty()
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Profile":
    badges = get_badges(selected_user)
    weekly_entries = get_entries_for_week(week_start, week_end, selected_user)
    weekly_done = len([x for x in weekly_entries if x["completed"]])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{selected_user} Profile</div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    p1.metric("Points", get_total_points(selected_user))
    p2.metric("Completed This Week", weekly_done)
    p3.metric("Badges", len(badges))

    st.subheader("Unlocked Badges")
    if badges:
        st.markdown("".join([f'<span class="badge">{badge}</span>' for badge in badges]), unsafe_allow_html=True)
    else:
        st.info("No badges yet.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Rewards":
    points = get_total_points(selected_user)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Rewards Shop</div>', unsafe_allow_html=True)
    st.write(f"Current points: **{points}**")

    for reward in REWARDS:
        st.markdown(
            f"""
            <div class="reward-tile">
                <div style="font-size:1.25rem;font-weight:800;">{reward["icon"]} {reward["name"]}</div>
                <div style="color:rgba(255,255,255,0.72);margin-top:4px;">Cost: {reward["cost"]} points</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if points >= reward["cost"]:
            if st.button(f"Request {reward['name']}", key=f"reward_{reward['name']}"):
                request_reward(selected_user, reward["name"], reward["cost"])
                st.success("Reward requested.")
        else:
            st.caption("Not enough points yet.")

    st.subheader("Reward Requests")
    rows = get_rewards(selected_user)
    if rows:
        for row in rows:
            status = "Approved" if row["approved"] else "Waiting for approval"
            st.write(f"{row['reward_name']} - {status}")
    else:
        st.info("No rewards requested yet.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Games":
    left, middle, right = st.columns(3, gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Treasure Grid</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">One hidden star. Nine tiles. Find it.</div>', unsafe_allow_html=True)
        st.write(st.session_state["treasure_message"])

        for row in range(3):
            cols = st.columns(3)
            for col in range(3):
                position = row * 3 + col
                if st.session_state["treasure_found"] and position == st.session_state["treasure_index"]:
                    label = "⭐"
                elif position in st.session_state["treasure_revealed"]:
                    label = "✖"
                else:
                    label = "?"
                if cols[col].button(label, key=f"treasure_{position}", use_container_width=True):
                    play_treasure(position)
                    st.rerun()

        if st.button("Reset Treasure Grid"):
            reset_treasure_game()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with middle:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Lucky Number</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Guess the hidden number from 1 to 10.</div>', unsafe_allow_html=True)
        st.write(st.session_state["lucky_message"])

        lucky_guess = st.number_input(
            "Your guess",
            min_value=1,
            max_value=10,
            step=1,
            value=5,
            key="lucky_guess",
        )

        if st.button("Guess Number"):
            submit_lucky_guess(int(lucky_guess))
            st.rerun()

        st.caption(f"Attempts: {st.session_state['lucky_attempts']}")

        if st.button("Reset Lucky Number"):
            reset_lucky_game()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Memory Flash</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Memorise the pattern and type it back.</div>', unsafe_allow_html=True)

        sequence_text = " - ".join(str(x) for x in st.session_state["memory_sequence"])
        st.info(f"Pattern: {sequence_text}")
        st.write(st.session_state["memory_message"])

        memory_input = st.text_input(
            "Enter the pattern",
            placeholder="Example: 1,2,3,4",
            key="memory_input_box",
        )

        if st.button("Check Pattern"):
            check_memory_game(memory_input)
            st.rerun()

        if st.button("New Pattern"):
            reset_memory_game()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "Parent Zone":
    if not is_parent_logged_in():
        st.warning("Parent login required.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Weekly Summary</div>', unsafe_allow_html=True)
        summary = get_weekly_summary(week_start, week_end)
        if summary.empty:
            st.info("No entries this week.")
        else:
            st.dataframe(
                summary.rename(
                    columns={
                        "person": "Person",
                        "total_entries": "Total Entries",
                        "completed_entries": "Completed",
                        "remaining_entries": "Remaining",
                        "total_points": "Points",
                        "completion_rate": "Completion %",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Reward Approvals</div>', unsafe_allow_html=True)
        rewards = get_rewards()
        pending = [row for row in rewards if not row["approved"]]
        if pending:
            for row in pending:
                st.write(f"{row['person']} requested {row['reward_name']} ({row['cost']} points)")
                if st.button(f"Approve #{row['id']}", key=f"approve_{row['id']}"):
                    approve_reward(row["id"])
                    st.success("Reward approved.")
                    st.rerun()
        else:
            st.info("No pending rewards.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">All Entries</div>', unsafe_allow_html=True)
        rows = get_all_entries()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No entries yet.")
        st.markdown("</div>", unsafe_allow_html=True)
