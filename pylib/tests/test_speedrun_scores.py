# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""End-to-end test of the three Speedrun scores through the proto seam.

Builds real flashcards (feed Memory) and tagged application questions (feed
Performance), logs graded attempts via the backend, and checks that the engine
returns Memory/Performance/Readiness with the honesty rules intact.
"""

import time

from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV
from tests.shared import getEmptyCol

QUESTION_TAG = "mcat-question"


def _add_flashcard(col):
    note = col.newNote()
    note["Front"] = "front"
    note["Back"] = "back"
    col.addNote(note)
    c = note.cards()[0]
    c.type = CARD_TYPE_REV
    c.queue = QUEUE_TYPE_REV
    c.due = col.sched.today - 5
    c.ivl = 10
    c.reps = 3
    col.update_card(c)
    return c.id


def _add_question(col, deck_id=None):
    note = col.newNote()
    note["Front"] = "stem"
    note["Back"] = "answer"
    note.tags.append(QUESTION_TAG)
    if deck_id is None:
        col.addNote(note)
    else:
        col.add_note(note, deck_id)
    return note.cards()[0].id


def test_three_scores_end_to_end():
    col = getEmptyCol()
    try:
        for _ in range(25):
            _add_flashcard(col)
        # 12 questions across 3 topics (4 each) so the per-topic depth gate for
        # Performance/Readiness is satisfied.
        for name in ("T1", "T2", "T3"):
            did = col.decks.id(name)
            for _ in range(4):
                q = _add_question(col, did)
                col._backend.speedrun_record_attempt(card_id=q, correct=True)

        s = col._backend.speedrun_scores()

        # Memory: known, and the 12 questions are NOT counted as studied cards.
        assert s.memory.known
        assert s.memory.studied_cards == 25

        # Performance: known, one attempt per question.
        assert s.performance.known
        assert s.performance.attempts == 12

        # Readiness: now projectable, on-scale, with an ordered range.
        assert s.readiness.known
        assert 472.0 <= s.readiness.projected <= 528.0
        assert s.readiness.low <= s.readiness.projected <= s.readiness.high
        assert "calibrated" in s.readiness.calibration_note.lower()
    finally:
        col.close()


def test_calibration_recorded_through_backend_recalibrates_readiness():
    col = getEmptyCol()
    try:
        for _ in range(25):
            _add_flashcard(col)
        for name in ("T1", "T2", "T3"):
            did = col.decks.id(name)
            for _ in range(4):
                q = _add_question(col, did)
                col._backend.speedrun_record_attempt(card_id=q, correct=True)

        before = col._backend.speedrun_scores()
        assert before.readiness.known
        assert "not yet calibrated" in before.readiness.calibration_note.lower()

        # Log a real full-length outcome via the backend RPC.
        projected = before.readiness.projected
        col._backend.speedrun_record_calibration(
            projected=projected, actual=projected + 3.0
        )

        after = col._backend.speedrun_scores()
        assert "off by" in after.readiness.calibration_note.lower()
        assert 472.0 <= after.readiness.projected <= 528.0

        # Out-of-scale inputs are clamped, not rejected, and still recalibrate.
        col._backend.speedrun_record_calibration(projected=999.0, actual=100.0)
        assert col._backend.speedrun_scores().readiness.known
    finally:
        col.close()


def test_exam_date_projection_through_backend():
    col = getEmptyCol()
    try:
        for _ in range(25):
            _add_flashcard(col)
        for name in ("T1", "T2", "T3"):
            did = col.decks.id(name)
            for _ in range(4):
                q = _add_question(col, did)
                col._backend.speedrun_record_attempt(card_id=q, correct=True)

        # No exam date by default: no projection, readiness reflects today.
        s0 = col._backend.speedrun_scores()
        assert not s0.readiness.has_exam
        assert not s0.memory.has_projection

        # Set an exam ~60 days out; projection + days-to-exam appear.
        ts = int(time.time()) + 60 * 86400
        col._backend.speedrun_set_exam_date(timestamp=ts)
        s1 = col._backend.speedrun_scores()
        assert s1.readiness.has_exam
        assert 55 <= s1.readiness.days_to_exam <= 61
        assert s1.memory.has_projection
        assert s1.memory.mean_stability_days >= 0.0

        # Clearing (0) removes the projection.
        col._backend.speedrun_set_exam_date(timestamp=0)
        assert not col._backend.speedrun_scores().readiness.has_exam
    finally:
        col.close()


def test_readiness_refused_without_application_questions():
    col = getEmptyCol()
    try:
        for _ in range(30):
            _add_flashcard(col)
        s = col._backend.speedrun_scores()
        # Strong memorization, but no applied evidence -> readiness withheld.
        assert s.memory.known
        assert not s.performance.known
        assert not s.readiness.known
        assert s.readiness.reason  # explains why it was withheld
    finally:
        col.close()
