import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

from practice_fastapi_tbd.gemini import FeedbackAnalysis


def analyze_feedback_via_api(feedback: str) -> FeedbackAnalysis:
    api_url = os.environ.get("FEEDBACK_API_URL", "http://127.0.0.1:8000").rstrip("/")
    request = Request(
        f"{api_url}/pookie",
        data=json.dumps({"prompt": feedback}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"Feedback API returned HTTP {error.code}: {detail}"
        ) from error

    if not isinstance(result, dict) or not isinstance(result.get("pookie"), dict):
        raise ValueError("Feedback API returned an invalid analysis response.")
    return FeedbackAnalysis.model_validate(result["pookie"])

st.set_page_config(page_title="Feedback Insights", page_icon="⭐")
st.title("Feedback Insights")
st.write("Collect customer feedback and see its overall sentiment and rating.")

if "feedback_items" not in st.session_state:
    st.session_state.feedback_items = []

with st.form("feedback_form", clear_on_submit=True):
    new_feedback = st.text_area(
        "Enter a piece of feedback",
        max_chars=2000,
        placeholder="What did the customer say?",
    )
    submitted = st.form_submit_button("Add feedback")

if submitted:
    if new_feedback.strip():
        st.session_state.feedback_items.append(new_feedback.strip())
        st.session_state.pop("analysis", None)
    else:
        st.warning("Enter some feedback before adding it.")

feedback_items = st.session_state.feedback_items
if feedback_items:
    st.subheader(f"Feedback collected ({len(feedback_items)})")
    for index, feedback in enumerate(feedback_items):
        feedback_column, remove_column = st.columns([8, 1])
        feedback_column.write(f"{index + 1}. {feedback}")
        if remove_column.button("Remove", key=f"remove_{index}"):
            feedback_items.pop(index)
            st.session_state.pop("analysis", None)
            st.rerun()

    analyze_clicked = st.button("Analyze all feedback", type="primary")
    if analyze_clicked:
        try:
            st.session_state.analysis = analyze_feedback_via_api(
                "\n\n".join(feedback_items)
            )
        except (RuntimeError, URLError, TimeoutError, OSError, ValueError) as error:
            st.error(f"Could not analyze the feedback: {error}")

    analysis = st.session_state.get("analysis")
    if analysis is not None:
        st.subheader("Overall results")
        sentiment_column, rating_column = st.columns(2)
        sentiment_column.metric("Overall sentiment", analysis.sentiment)
        rating_column.metric(
            "Overall rating",
            f"{'★' * analysis.rating}{'☆' * (5 - analysis.rating)}",
            f"{analysis.rating} out of 5",
        )
        st.write(analysis.summary)
else:
    st.info("Add one or more feedback entries to get started.")
