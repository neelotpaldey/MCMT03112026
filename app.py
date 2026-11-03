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
    1: "Room 1 - IGNOU Cabin",
    2: "Room 2 - Meeting Room",
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

