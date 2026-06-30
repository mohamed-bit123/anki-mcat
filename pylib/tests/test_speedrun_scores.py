# Copyright: MCAT Speedrun fork
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""End-to-end test of the three Speedrun scores through the proto seam.

Builds real flashcards (feed Memory) and tagged application questions (feed
Performance), logs graded attempts via the backend, and checks that the engine
returns Memory/Performance/Readiness with the honesty rules intact.
"""

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


def _add_question(col):
    note = col.newNote()
    note["Front"] = "stem"
    note["Back"] = "answer"
    note.tags.append(QUESTION_TAG)
    col.addNote(note)
    return note.cards()[0].id


def test_three_scores_end_to_end():
    col = getEmptyCol()
    try:
        for _ in range(25):
            _add_flashcard(col)
        for _ in range(12):
            q = _add_question(col)
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
