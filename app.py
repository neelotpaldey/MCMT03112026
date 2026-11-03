import os
import sqlite3
import time

import streamlit as st

# ---------------------------------------------------------------
# Interview Queue Tracker (2 rooms, groups of 3)
# Tab 1: Faculty  - the faculty outside a room picks that room and marks In / Out / Abs
# Tab 2: Live View - for students waiting in the common room
# State is stored in a SQLite file, so every browser sees the same data.
# ---------------------------------------------------------------

DB_FILE = "interview.db"
FACULTY_PIN = os.environ.get("FACULTY_PIN", "1234")
REFRESH_SECONDS = 5
BATCH_SIZE = 3  # students who go in together

ROOMS = {
    1: "Room 1 - Meeting Room",
    2: "Room 2 - IGNOU Cabin",
}

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
        "status TEXT NOT NULL DEFAULT 'Waiting', "
        "room INTEGER)"
    )
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(students)").fetchall()]
    if "room" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN room INTEGER")
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
        "SELECT sr, name, status, room FROM students ORDER BY sr"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_status(sr, status, room=None):
    conn = get_conn()
    if status == IN:
        conn.execute(
            "UPDATE students SET status = ?, room = ? WHERE sr = ?",
            (status, room, sr),
        )
    elif status == OUT:
        # keep the room so the record shows where the interview happened
        conn.execute("UPDATE students SET status = ? WHERE sr = ?", (status, sr))
    else:
        conn.execute(
            "UPDATE students SET status = ?, room = NULL WHERE sr = ?",
            (status, sr),
        )
    conn.commit()
    conn.close()


def mark_many_out(srs):
    conn = get_conn()
    for sr in srs:
        conn.execute("UPDATE students SET status = ? WHERE sr = ?", (OUT, sr))
    conn.commit()
    conn.close()


def call_next_group(room):
    # Done in one locked transaction so two faculty pressing together
    # can never pick the same students.
    conn = get_conn()
    conn.execute("BEGIN IMMEDIATE")
    rows = conn.execute(
        "SELECT sr FROM students WHERE status = ? ORDER BY sr LIMIT ?",
        (WAITING, BATCH_SIZE),
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE students SET status = ?, room = ? WHERE sr = ?",
            (IN, room, row["sr"]),
        )
    conn.commit()
    conn.close()


def reset_all():
    conn = get_conn()
    conn.execute("UPDATE students SET status = ?, room = NULL", (WAITING,))
    conn.commit()
    conn.close()


# ---------------- small display helpers ----------------

def short(r):
    return "#" + str(r["sr"]) + "  " + r["name"]


def status_label(r):
    if r["status"] == IN:
        return "🟢 In - " + ROOMS.get(r["room"], "")
    if r["status"] == OUT:
        return "✅ Done"
    if r["status"] == ABSENT:
        return "❌ Absent"
    return "⏳ Waiting"


# ---------------- Live View tab ----------------

if hasattr(st, "fragment"):
    auto_refresh = st.fragment(run_every=REFRESH_SECONDS)
else:
    # very old Streamlit: no auto refresh, the page must be reloaded by hand
    def auto_refresh(func):
        return func


@auto_refresh
def view_panel():
    rows = fetch_all()
    waiting = [r for r in rows if r["status"] == WAITING]
    inside = [r for r in rows if r["status"] == IN]
    done = [r for r in rows if r["status"] == OUT]
    absent = [r for r in rows if r["status"] == ABSENT]

    col1, col2, col3 = st.columns(3)
    room_cols = {1: col1, 2: col2}

    for room_no in ROOMS:
        with room_cols[room_no]:
            st.markdown("### 🚪 " + ROOMS[room_no])
            group = [r for r in inside if r["room"] == room_no]
            if group:
                st.markdown("**🟢 In interview now**")
                for r in group:
                    st.success(short(r))
            else:
                st.info("Free right now")

    with col3:
        st.markdown("### ⏳ Waiting (" + str(len(waiting)) + ")")
        if waiting:
            st.markdown("**⏭️ Next group - be ready at the rooms**")
            for r in waiting[:BATCH_SIZE]:
                st.warning(short(r))
            later = waiting[BATCH_SIZE:BATCH_SIZE * 2]
            if later:
                st.markdown("**Get ready after that**")
                for r in later:
                    st.info(short(r))
            rest = waiting[BATCH_SIZE * 2:]
            if rest:
                st.markdown("**Remaining**")
                for r in rest:
                    st.write(short(r))
        else:
            st.write("No one is waiting.")

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Waiting", len(waiting))
    c2.metric("In", len(inside))
    c3.metric("Done", len(done))
    c4.metric("Absent", len(absent))

    st.markdown("### Full list")
    table = []
    for r in rows:
        table.append(
            {"#": r["sr"], "Name": r["name"], "Status": status_label(r)}
        )
    try:
        st.dataframe(table, hide_index=True, width="stretch", height=420)
    except TypeError:
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

    room = st.radio(
        "I am the faculty outside:",
        list(ROOMS.keys()),
        format_func=ROOMS.get,
        horizontal=True,
        key="my_room",
    )
    other = 2 if room == 1 else 1

    rows = fetch_all()
    mine = [r for r in rows if r["status"] == IN and r["room"] == room]
    theirs = [r for r in rows if r["status"] == IN and r["room"] == other]
    waiting = [r for r in rows if r["status"] == WAITING]

    st.markdown("## " + ROOMS[room])

    st.markdown("### Currently inside")
    if mine:
        for r in mine:
            a, b = st.columns([3, 1])
            a.success(short(r))
            b.button("Out", key="top_out_" + str(r["sr"]),
                     on_click=set_status, args=(r["sr"], OUT))
        st.button("Mark ALL inside as OUT", key="all_out", type="primary",
                  on_click=mark_many_out, args=([r["sr"] for r in mine],))
    else:
        st.info("Room is empty.")

    st.markdown("### Next group")
    if waiting:
        for r in waiting[:BATCH_SIZE]:
            a, b = st.columns([3, 1])
            a.warning(short(r))
            b.button("Abs", key="grp_abs_" + str(r["sr"]),
                     on_click=set_status, args=(r["sr"], ABSENT))
        st.button("Call next group into this room", key="group_in", type="primary",
                  disabled=len(mine) > 0,
                  on_click=call_next_group, args=(room,))
        if mine:
            st.caption("Mark the current group OUT first.")
        else:
            st.caption("Takes the next " + str(BATCH_SIZE) + " waiting students. Marking Abs pulls the next student into the group.")
    else:
        st.write("No one is waiting.")

    if theirs:
        names = ", ".join([r["name"] for r in theirs])
        st.caption(ROOMS[other] + " is busy with: " + names)
    else:
        st.caption(ROOMS[other] + " is free.")

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
        c0, c1, c2, c3, c4, c5 = st.columns([0.6, 3, 2.6, 0.9, 0.9, 0.9])
        c0.write(str(sr))
        c1.write(r["name"])
        c2.write(status_label(r))
        c3.button("In", key="in_" + str(sr), on_click=set_status, args=(sr, IN, room))
        c4.button("Out", key="out_" + str(sr), on_click=set_status, args=(sr, OUT))
        c5.button("Abs", key="abs_" + str(sr), on_click=set_status, args=(sr, ABSENT))

    st.divider()
    with st.expander("More"):
        st.caption("Tip: to undo a mistake, press the correct button again (e.g. Abs → In). The row's In button sends that student into the room selected above.")
        sure = st.checkbox("I want to reset everyone to Waiting")
        if st.button("Reset all", disabled=not sure):
            reset_all()
            st.rerun()


# ---------------- page ----------------

st.set_page_config(page_title="Interview Tracker", page_icon="🎤", layout="wide")
init_db()

st.title("🎤 Interview Tracker")

tab_faculty, tab_view = st.tabs(["🧑‍🏫 Faculty (mark In / Out / Abs)", "👀 Live View"])

with tab_faculty:
    faculty_panel()

with tab_view:
    view_panel()
