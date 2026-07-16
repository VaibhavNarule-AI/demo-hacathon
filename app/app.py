# Interview Note Summarizer — Sprint 2: candidates + SQLite storage
#
# How to run locally:
#   1. export ANTHROPIC_API_KEY=sk-ant-...
#   2. pip install -r requirements.txt
#   3. streamlit run app.py
#
# (No key hardcoded here — reads ANTHROPIC_API_KEY from the environment, falling
# back to st.secrets["ANTHROPIC_API_KEY"] for Streamlit Cloud deployment.)
#
# Storage: SQLite file `candidates.db`, created next to this app.py on first run.

import os
import json
import sqlite3
from datetime import datetime

import streamlit as st
import anthropic

MODEL = "claude-sonnet-5"
NEW_CANDIDATE_OPTION = "+ Add new candidate"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidates.db")

st.set_page_config(page_title="Interview Note Summarizer", page_icon="📝")
st.title("Interview Note Summarizer")


# --------------------------------------------------------------------------
# Storage (SQLite) — one local file, table created on first run if missing.
# --------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            notes TEXT,
            strengths TEXT,
            concerns TEXT,
            overall_rating INTEGER,
            recommendation TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_all_candidate_names():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name FROM candidates ORDER BY name").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_candidate_by_name(name):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT name, notes, strengths, concerns, overall_rating, recommendation "
        "FROM candidates WHERE name = ?",
        (name,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "name": row[0],
        "notes": row[1] or "",
        "strengths": json.loads(row[2]) if row[2] else [],
        "concerns": json.loads(row[3]) if row[3] else [],
        "overall_rating": row[4],
        "recommendation": row[5],
    }


def save_candidate(name, notes_text, result):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO candidates (name, notes, strengths, concerns, overall_rating, recommendation, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            notes=excluded.notes,
            strengths=excluded.strengths,
            concerns=excluded.concerns,
            overall_rating=excluded.overall_rating,
            recommendation=excluded.recommendation,
            updated_at=excluded.updated_at
        """,
        (
            name,
            notes_text,
            json.dumps(result.get("strengths", [])),
            json.dumps(result.get("concerns", [])),
            result.get("overall_rating"),
            result.get("recommendation"),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


init_db()


# --------------------------------------------------------------------------
# Candidate picker (sidebar) — pick existing or add new
# --------------------------------------------------------------------------
existing_names = get_all_candidate_names()
options = [NEW_CANDIDATE_OPTION] + existing_names

st.sidebar.header("Candidate")
choice = st.sidebar.selectbox("Pick or add a candidate", options)

new_name = ""
if choice == NEW_CANDIDATE_OPTION:
    new_name = st.sidebar.text_input("New candidate name")
    candidate_name = new_name.strip()
else:
    candidate_name = choice

# candidate_key identifies which candidate is "active" for the purpose of
# knowing when to (re)load their saved notes/summary into the page.
candidate_key = choice if choice != NEW_CANDIDATE_OPTION else "__new__"

if "loaded_for" not in st.session_state:
    st.session_state.loaded_for = None
if "summary_result" not in st.session_state:
    st.session_state.summary_result = None
if "is_mock_result" not in st.session_state:
    st.session_state.is_mock_result = False

if st.session_state.loaded_for != candidate_key:
    st.session_state.loaded_for = candidate_key
    st.session_state.summary_result = None
    st.session_state.is_mock_result = False
    if choice == NEW_CANDIDATE_OPTION:
        st.session_state["notes_input"] = ""
    else:
        saved = get_candidate_by_name(choice)
        if saved:
            st.session_state["notes_input"] = saved["notes"]
            if saved["strengths"] or saved["concerns"] or saved["recommendation"]:
                st.session_state.summary_result = {
                    "strengths": saved["strengths"],
                    "concerns": saved["concerns"],
                    "overall_rating": saved["overall_rating"],
                    "recommendation": saved["recommendation"],
                }
        else:
            st.session_state["notes_input"] = ""

st.subheader(f"Candidate: {candidate_name if candidate_name else '(unnamed — type a name in the sidebar)'}")

notes = st.text_area(
    "Paste free-text interview notes here",
    height=250,
    key="notes_input",
    placeholder="e.g. Strong on system design, walked through a distributed cache "
    "tradeoff clearly. Seemed hesitant when asked about leading a team...",
)

summarize_clicked = st.button("Summarize", type="primary")


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        # Only touch st.secrets if a secrets file actually exists — accessing
        # st.secrets when no secrets.toml is present anywhere makes Streamlit
        # itself render its own st.error() with local file paths, on top of
        # the clean message below. Checking existence first avoids that.
        secrets_files = st.config.get_option("secrets.files") or []
        if not any(os.path.exists(p) for p in secrets_files):
            return None
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return None


def call_claude_for_summary(notes_text: str) -> dict:
    """Call Claude with a forced tool call to get back structured JSON."""
    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    tool = {
        "name": "record_interview_summary",
        "description": (
            "Record a structured summary of an interview based on free-text notes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key strengths the candidate demonstrated.",
                },
                "concerns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Concerns or gaps, including ones only implied by the notes.",
                },
                "overall_rating": {
                    "type": "integer",
                    "description": "Overall rating from 1 (poor) to 5 (excellent).",
                },
                "recommendation": {
                    "type": "string",
                    "description": "A short hiring recommendation, e.g. 'Strong hire', "
                    "'Hire with reservations', 'No hire'.",
                },
            },
            "required": ["strengths", "concerns", "overall_rating", "recommendation"],
            "additionalProperties": False,
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[tool],
        tool_choice={"type": "tool", "name": "record_interview_summary"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Here are free-text interview notes for a candidate. Analyze them "
                    "and record a structured summary using the tool provided. Infer "
                    "reasonable concerns even if not stated outright, and weigh "
                    "conflicting signals into one overall judgment.\n\n"
                    f"Notes:\n{notes_text}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_interview_summary":
            return block.input

    raise RuntimeError("Claude did not return the expected structured tool call.")


MOCK_RESULT = {
    "strengths": [
        "Clear communicator, walked through technical tradeoffs step by step",
        "Solid hands-on experience directly relevant to the role",
    ],
    "concerns": [
        "Limited detail on handling ambiguity or conflicting priorities",
        "Some hesitation when asked about leading or mentoring others",
    ],
    "overall_rating": 4,
    "recommendation": "Hire with reservations",
}

if summarize_clicked:
    if not notes.strip():
        st.warning("Paste some interview notes first.")
    elif not get_api_key():
        st.session_state.summary_result = MOCK_RESULT
        st.session_state.is_mock_result = True
    else:
        try:
            with st.spinner("Summarizing with Claude..."):
                result = call_claude_for_summary(notes)

            # Validate the shape before trusting it — a bad/partial tool call
            # should show a clear message, never crash the app.
            required_fields = ["strengths", "concerns", "overall_rating", "recommendation"]
            missing = [f for f in required_fields if f not in result]
            if missing:
                raise ValueError(f"Claude's response was missing fields: {', '.join(missing)}")

            st.session_state.summary_result = result
            st.session_state.is_mock_result = False
        except Exception as e:
            st.error(
                "Couldn't get a usable summary back from Claude (bad/partial response "
                f"or an API issue). Details: {e}"
            )

# --------------------------------------------------------------------------
# Render current summary (freshly generated or loaded from storage) + Save
# --------------------------------------------------------------------------
result = st.session_state.summary_result
if result:
    if st.session_state.is_mock_result:
        st.warning(
            "⚠️ DEMO MODE — no live ANTHROPIC_API_KEY configured. This is a mocked "
            "example result, not a real Claude call."
        )
    st.success("Summary")

    st.markdown("### Strengths")
    for s in result.get("strengths", []):
        st.markdown(f"- {s}")

    st.markdown("### Concerns")
    for c in result.get("concerns", []):
        st.markdown(f"- {c}")

    st.markdown("### Overall Rating")
    st.markdown(f"**{result.get('overall_rating', 'N/A')} / 5**")

    st.markdown("### Recommendation")
    st.markdown(f"**{result.get('recommendation', 'N/A')}**")

    save_clicked = st.button("Save")
    if save_clicked:
        if not candidate_name:
            st.warning("Type a candidate name in the sidebar before saving.")
        else:
            try:
                save_candidate(candidate_name, notes, result)
                st.success(f"Saved to {candidate_name}'s record.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save to storage. Details: {e}")
