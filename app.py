from datetime import date, datetime, timedelta, time
from pathlib import Path

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
        "start": "#0f4c81",
        "end": "#3fa7d6",
        "soft": "#eaf6fb",
    },
    "Isabel": {
        "start": "#b85c38",
        "end": "#f0a04b",
        "soft": "#fff4ea",
    },
}


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


def add_entry(person, entry_date, entry_time, activity, category, notes):
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


def get_weekly_summary(start_date, end_date):
    supabase = get_supabase()
    response = (
        supabase.table("entries")
        .select("*")
        .gte("entry_date", start_date.isoformat())
        .lte("entry_date", end_date.isoformat())
        .execute()
    )

    rows = response.data

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    summary = (
        df.groupby("person")
        .agg(
            total_entries=("id", "count"),
            completed_entries=("completed", "sum"),
        )
        .reset_index()
    )

    summary["completed_entries"] = summary["completed_entries"].astype(int)
    summary["remaining_entries"] = summary["total_entries"] - summary["completed_entries"]
    return summary


def format_entry_title(entry):
    status = "Complete" if entry["completed"] else "To do"
    return f"{entry['entry_time']} | {entry['activity']} | {entry['category']} | {status}"


def is_parent_logged_in():
    return st.session_state.get("parent_logged_in", False)


st.set_page_config(page_title="Daily Tracker", page_icon="DT", layout="wide")

selected_user = st.sidebar.selectbox("Choose a person", USERS)
colors = PERSON_COLORS[selected_user]

st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            radial-gradient(circle at top left, {colors["soft"]} 0%, #f7f9fc 38%, #eef3f8 100%);
    }}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }}

    .hero {{
        background: linear-gradient(135deg, {colors["start"]}, {colors["end"]});
        color: white;
        border-radius: 28px;
        padding: 28px 30px;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.12);
        margin-bottom: 24px;
    }}

    .hero-title {{
        font-size: 2.3rem;
        font-weight: 800;
        margin: 0;
    }}

    .hero-subtitle {{
        font-size: 1rem;
        opacity: 0.95;
        margin-top: 8px;
    }}

    .card {{
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(15, 76, 129, 0.08);
        border-radius: 24px;
        padding: 20px;
        box-shadow: 0 12px 28px rgba(31, 50, 81, 0.08);
        margin-bottom: 20px;
    }}

    .photo-card {{
        background: rgba(255, 255, 255, 0.92);
        border-radius: 24px;
        padding: 18px;
        box-shadow: 0 12px 28px rgba(31, 50, 81, 0.08);
        text-align: center;
    }}

    .section-title {{
        font-size: 1.3rem;
        font-weight: 700;
        color: #1f2f46;
        margin-bottom: 8px;
    }}

    .section-copy {{
        color: #5b677a;
        margin-bottom: 14px;
    }}

    .entry-chip {{
        display: inline-block;
        background: {colors["soft"]};
        color: #234;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 0.9rem;
        margin-bottom: 12px;
    }}

    .stButton > button {{
        border: none;
        border-radius: 14px;
        padding: 0.65rem 1.1rem;
        font-weight: 700;
        background: linear-gradient(135deg, {colors["start"]}, {colors["end"]});
        color: white;
        box-shadow: 0 10px 20px rgba(15, 76, 129, 0.18);
    }}

    .stButton > button:hover {{
        color: white;
        filter: brightness(0.98);
    }}

    .stTextInput input, .stTextArea textarea, .stDateInput input, .stTimeInput input {{
        border-radius: 14px;
    }}

    div[data-testid="stSelectbox"] > div {{
        border-radius: 14px;
    }}

    div[data-testid="stDataFrame"] {{
        border-radius: 18px;
        overflow: hidden;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.write("Add a new entry, then mark it complete below.")
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
        <div class="hero-title">Daily Activity Tracker</div>
        <div class="hero-subtitle">{selected_user}'s daily planner, routine tracker, and progress board.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

top_left, top_right = st.columns([1.2, 2])

with top_left:
    st.markdown('<div class="photo-card">', unsafe_allow_html=True)
    photo_file = find_photo(selected_user)
    if photo_file:
        st.image(photo_file, width=240)
    else:
        st.info(f"No photo found for {selected_user}. Upload {selected_user.lower()}.jpg or .png")
    st.markdown(f"### {selected_user}")
    st.caption("Choose a person from the sidebar to switch pages.")
    st.markdown("</div>", unsafe_allow_html=True)

with top_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Add Entry</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Add an activity, choose a time and category, and save it to the tracker.</div>',
        unsafe_allow_html=True,
    )

    with st.form("add_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            entry_date = st.date_input("Date", value=date.today())
            activity = st.text_input("Activity", placeholder="Example: Homework, football, reading")
            category = st.selectbox("Category", CATEGORIES)

        with col2:
            entry_time = st.time_input("Time", value=time(9, 0))
            person = st.selectbox("Person", USERS, index=USERS.index(selected_user))
            notes = st.text_area("Notes", placeholder="Optional notes")

        submitted = st.form_submit_button("Save entry")

        if submitted:
            if not activity.strip():
                st.error("Please enter an activity.")
            else:
                add_entry(person, entry_date, entry_time, activity, category, notes)
                st.success("Entry saved.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

today = date.today()
today_entries = get_entries_for_day(today, selected_user)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(
    f'<div class="section-title">Today\'s Entries for {selected_user}</div>',
    unsafe_allow_html=True,
)

if not today_entries:
    st.info("No entries yet for today.")
else:
    for entry in today_entries:
        left_col, right_col = st.columns([5, 1])

        with left_col:
            with st.container(border=True):
                st.markdown(f'<div class="entry-chip">{entry["category"]}</div>', unsafe_allow_html=True)
                st.markdown(f"**{format_entry_title(entry)}**")
                if entry["notes"]:
                    st.write(entry["notes"])

        with right_col:
            if entry["completed"]:
                st.success("Done")
            else:
                if st.button("Mark complete", key=f"complete_{entry['id']}"):
                    mark_entry_complete(entry["id"])
                    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

if is_parent_logged_in():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Weekly Summary</div>', unsafe_allow_html=True)

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    st.write(
        f"Showing entries from {week_start.strftime('%d %b %Y')} to {week_end.strftime('%d %b %Y')}."
    )

    weekly_summary = get_weekly_summary(week_start, week_end)

    if weekly_summary.empty:
        st.info("No entries have been added this week.")
    else:
        st.dataframe(
            weekly_summary.rename(
                columns={
                    "person": "Person",
                    "total_entries": "Total Entries",
                    "completed_entries": "Completed",
                    "remaining_entries": "Remaining",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        chart_data = weekly_summary.set_index("person")[["completed_entries", "remaining_entries"]]
        st.bar_chart(chart_data)

    st.markdown("</div>", unsafe_allow_html=True)
