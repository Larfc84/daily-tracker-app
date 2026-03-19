import sqlite3
from datetime import date, datetime, timedelta, time

import pandas as pd
import streamlit as st


DB_NAME = "daily_tracker.db"
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


def get_connection():
    connection = sqlite3.connect(DB_NAME, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def create_table():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                activity TEXT NOT NULL,
                category TEXT NOT NULL,
                notes TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


def add_entry(person, entry_date, entry_time, activity, category, notes):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO entries (
                person,
                entry_date,
                entry_time,
                activity,
                category,
                notes,
                completed,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                person,
                entry_date.isoformat(),
                entry_time.strftime("%H:%M"),
                activity.strip(),
                category,
                notes.strip(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def mark_entry_complete(entry_id):
    with get_connection() as connection:
        connection.execute(
            "UPDATE entries SET completed = 1 WHERE id = ?",
            (entry_id,),
        )


def get_entries_for_day(selected_date, person=None):
    query = """
        SELECT *
        FROM entries
        WHERE entry_date = ?
    """
    params = [selected_date.isoformat()]

    if person:
        query += " AND person = ?"
        params.append(person)

    query += " ORDER BY entry_time ASC, id ASC"

    with get_connection() as connection:
        return connection.execute(query, params).fetchall()


def get_weekly_summary(start_date, end_date):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                person,
                COUNT(*) AS total_entries,
                SUM(completed) AS completed_entries
            FROM entries
            WHERE entry_date BETWEEN ? AND ?
            GROUP BY person
            ORDER BY person
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

    summary = pd.DataFrame(rows, columns=["person", "total_entries", "completed_entries"])

    if summary.empty:
        return summary

    summary["completed_entries"] = summary["completed_entries"].fillna(0).astype(int)
    summary["remaining_entries"] = summary["total_entries"] - summary["completed_entries"]
    return summary


def format_entry_title(entry):
    status = "Complete" if entry["completed"] else "To do"
    return f'{entry["entry_time"]} | {entry["activity"]} | {entry["category"]} | {status}'


create_table()

st.set_page_config(page_title="Daily Tracker", page_icon="DT", layout="wide")

st.title("Daily Activity Tracker")
st.caption("A simple app for Laurence and Isabel to track what they do in a day.")

selected_user = st.sidebar.selectbox("Choose a person", USERS)
st.sidebar.write("Add a new entry, then mark it complete below.")

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
