from datetime import date, datetime, timedelta, time

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

PHOTO_PATHS = {
    "Laurence": "laurence.jpg",
    "Isabel": "isabel.jpg",
}

selected_user = st.sidebar.selectbox("Choose a person", USERS)

photo_file = PHOTO_PATHS.get(selected_user)
try:
    st.image(photo_file, width=220)
except Exception:
    st.warning(f"Photo not found: {photo_file}")

}


@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


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

st.title("Daily Activity Tracker")
st.caption("A simple app for Laurence and Isabel to track what they do in a day.")

selected_user = st.sidebar.selectbox("Choose a person", USERS)
st.image(PHOTO_PATHS[selected_user], width=220)
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

with st.form("add_entry_form", clear_on_submit=True):
    st.subheader("Add Entry")
    col1, col2 = st.columns(2)

    with col1:
        entry_date = st.date_input("Date", value=date.today())
        activity = st.text_input("Activity")
        category = st.selectbox("Category", CATEGORIES)

    with col2:
        entry_time = st.time_input("Time", value=time(9, 0))
        person = st.selectbox("Person", USERS, index=USERS.index(selected_user))
        notes = st.text_area("Notes")

    submitted = st.form_submit_button("Save entry")

    if submitted:
        if not activity.strip():
            st.error("Please enter an activity.")
        else:
            add_entry(person, entry_date, entry_time, activity, category, notes)
            st.success("Entry saved.")
            st.rerun()

st.divider()

today = date.today()
st.subheader(f"Today's Entries for {selected_user}")
today_entries = get_entries_for_day(today, selected_user)

if not today_entries:
    st.info("No entries yet for today.")
else:
    for entry in today_entries:
        left_col, right_col = st.columns([5, 1])

        with left_col:
            with st.container(border=True):
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

if is_parent_logged_in():
    st.divider()

    st.subheader("Weekly Summary")
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
