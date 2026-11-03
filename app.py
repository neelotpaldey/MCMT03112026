import os
import sqlite3
import time

import streamlit as st

# ---------------------------------------------------------------
# Interview Queue Tracker
# Tab 1: Faculty (marks In / Out / Absent, PIN protected)
# Tab 2: Live View (for students sitting in other rooms)
# State is stored in a SQLite file, so every browser sees the same data.
# ---------------------------------------------------------------

DB_FILE = "interview.db"
FACULTY_PIN = os.environ.get("FACULTY_PIN", "1234")
REFRESH_SECONDS = 5
BATCH_SIZE = 3  # students who go in together

NAMES = [
    "Lankshika Singh", "Srishti Sharma", "Radha", "Simmi Maurya",
    "Priya Verma", "Shivam Dubey", "Kumkum Patel", "Kartik Singh",
    "Prakhar Srivastav", "Kashish Maurya", "Kritika Gupta",
    "Shubham Kumar Gond", "Shruti Rai", "Divyansh Jaiswal",
    "Lavyansh Vishwakarma", "Raj Sharma", "Ashish Patel", "Ritik Yadav",
    "Divyanshu Pandey", "Suryansh Tripathi", "Shahira Sohail",
    "Sudhir Yadav", "Himanshu Kumar", "Payal Mishra", "Saptak Das",
    "Chanchal Bharti", "Harsh Maurya", "Arun Kumar", "Vishrut Baranwal",
    "Hariom Sharma", "Jahnvi Dubey", "Neha Yadav", "Riya Muskan",
    "Vikki Kumar", "Anshuman Chaurasia", "Nikhil Tiwari", "Subrat Jha",
    "Chandramauli Upadhyay", "Aftab Alam", "Arshad Kamal",
    "Amit Devbanshi", "Gunjan Kumari", "Shreyashi Singh",
]

WAITING = "Waiting"
IN = "In"
OUT = "Out"
ABSENT = "Absent"

STATUS_LABEL = {
    WAITING: "⏳ Waiting",
    IN: "🟢 In interview",
    OUT: "✅ Done (Out)",
    ABSENT: "❌ Absent",
}


# ---------------- database helpers ----------------

def get_conn():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS students ("
        "sr INTEGER PRIMARY KEY, "
        "name TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'Waiting')"
    )
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        for number, name in enumerate(NAMES, start=1):
            conn.execute(
                "INSERT INTO students (sr, name, status) VALUES (?, ?, ?)",
                (number, name, WAITING),
            )
    conn.commit()
    conn.close()


def fetch_all():
    conn = get_conn()
    rows = conn.execute(
        "SELECT sr, name, status FROM students ORDER BY sr"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_status(sr, status):
    conn = get_conn()
    conn.execute("UPDATE students SET status = ? WHERE sr = ?", (status, sr))
    conn.commit()
    conn.close()


def set_many(srs, status):
    conn = get_conn()
    for sr in srs:
        conn.execute("UPDATE students SET status = ? WHERE sr = ?", (status, sr))
    conn.commit()
    conn.close()


def reset_all():
    conn = get_conn()
    conn.execute("UPDATE students SET status = ?", (WAITING,))
    conn.commit()
    conn.close()


# ---------------- Live View tab ----------------

@st.fragment(run_every=REFRESH_SECONDS)
def view_panel():
    rows = fetch_all()
    inside = [r for r in rows if r["status"] == IN]
    waiting = [r for r in rows if r["status"] == WAITING]
    done = [r for r in rows if r["status"] == OUT]
    absent = [r for r in rows if r["status"] == ABSENT]

    st.markdown("### 🟢 Now in interview")
    if inside:
        for r in inside:
            st.success("#" + str(r["sr"]) + "  " + r["name"])
    else:
        st.info("Interview room is free right now.")

    st.markdown("### ⏭️ Next group")
    if waiting:
        st.warning("Please be at the interview room:")
        for r in waiting[:BATCH_SIZE]:
            st.write("#" + str(r["sr"]) + "  " + r["name"])
        later = waiting[BATCH_SIZE:BATCH_SIZE * 2]
        if later:
            st.markdown("**Get ready (the group after that):**")
            for r in later:
                st.write("#" + str(r["sr"]) + "  " + r["name"])
    else:
        st.write("No one is waiting.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Waiting", len(waiting))
    c2.metric("In", len(inside))
    c3.metric("Done", len(done))
    c4.metric("Absent", len(absent))

    st.markdown("### Full list")
    table = []
    for r in rows:
        table.append(
            {"#": r["sr"], "Name": r["name"], "Status": STATUS_LABEL[r["status"]]}
        )
    st.dataframe(table, hide_index=True, use_container_width=True, height=420)

    st.caption("Auto-refreshes every " + str(REFRESH_SECONDS) + " seconds · last update " + time.strftime("%I:%M:%S %p"))


# ---------------- Faculty tab ----------------

def faculty_panel():
    if not st.session_state.get("faculty_ok"):
        pin = st.text_input("Faculty PIN", type="password")
        if st.button("Unlock"):
            if pin == FACULTY_PIN:
                st.session_state["faculty_ok"] = True
                st.rerun()
            else:
                st.error("Wrong PIN")
        return

    rows = fetch_all()
    inside = [r for r in rows if r["status"] == IN]
    waiting = [r for r in rows if r["status"] == WAITING]

    st.markdown("### Currently inside")
    if inside:
        for r in inside:
            a, b = st.columns([3, 1])
            a.success("#" + str(r["sr"]) + "  " + r["name"])
            b.button("Out", key="top_out_" + str(r["sr"]),
                     on_click=set_status, args=(r["sr"], OUT))
        st.button("Mark ALL inside as OUT", key="all_out", type="primary",
                  on_click=set_many, args=([r["sr"] for r in inside], OUT))
    else:
        st.info("Room is empty.")

    st.markdown("### Next group")
    if waiting:
        group = waiting[:BATCH_SIZE]
        for r in group:
            a, b = st.columns([3, 1])
            a.warning("#" + str(r["sr"]) + "  " + r["name"])
            b.button("Abs", key="grp_abs_" + str(r["sr"]),
                     on_click=set_status, args=(r["sr"], ABSENT))
        st.button("Send this group IN", key="group_in", type="primary",
                  on_click=set_many, args=([r["sr"] for r in group], IN))
        st.caption("Marking someone Abs pulls the next waiting student into this group.")
    else:
        st.write("No one is waiting.")

    st.divider()
    st.markdown("### All students")
    choice = st.radio(
        "Show",
        ["All", WAITING, IN, OUT, ABSENT],
        horizontal=True,
        label_visibility="collapsed",
    )

    for r in rows:
        if choice != "All" and r["status"] != choice:
            continue
        sr = r["sr"]
        c0, c1, c2, c3, c4, c5 = st.columns([0.6, 3, 2.2, 0.9, 0.9, 0.9])
        c0.write(str(sr))
        c1.write(r["name"])
        c2.write(STATUS_LABEL[r["status"]])
        c3.button("In", key="in_" + str(sr), on_click=set_status, args=(sr, IN))
        c4.button("Out", key="out_" + str(sr), on_click=set_status, args=(sr, OUT))
        c5.button("Abs", key="abs_" + str(sr), on_click=set_status, args=(sr, ABSENT))

    st.divider()
    with st.expander("More"):
        st.caption("Tip: to undo a mistake, press the correct button again (e.g. Abs → In).")
        sure = st.checkbox("I want to reset everyone to Waiting")
        if st.button("Reset all", disabled=not sure):
            reset_all()
            st.rerun()


# ---------------- page ----------------

st.set_page_config(page_title="Interview Tracker", page_icon="🎤", layout="centered")
init_db()

st.title("🎤 Interview Tracker")

tab_faculty, tab_view = st.tabs(["🧑‍🏫 Faculty (mark In / Out / Abs)", "👀 Live View"])

with tab_faculty:
    faculty_panel()

with tab_view:
    view_panel()
