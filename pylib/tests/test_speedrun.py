# Copyright: MCAT Speedrun fork
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""End-to-end test of the Speedrun points-at-stake review ordering.

Exercises the real Rust engine change (rslib/src/speedrun/queue.rs) through the
protobuf seam and the Python API, proving the new ReviewCardOrder reaches the
desktop app and reorders the study queue as designed.
"""

from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV
from tests.shared import getEmptyCol

# anki_proto deck_config.ReviewCardOrder values
REVIEW_ORDER_RELATIVE_OVERDUENESS = 12
REVIEW_ORDER_SPEEDRUN_POINTS_AT_STAKE = 13


def _add_review_card(col, front, *, overdue_days, interval, lapses):
    note = col.newNote()
    note["Front"] = front
    note["Back"] = "back"
    col.addNote(note)
    card = note.cards()[0]
    card.type = CARD_TYPE_REV
    card.queue = QUEUE_TYPE_REV
    card.due = col.sched.today - overdue_days
    card.ivl = interval
    card.lapses = lapses
    col.update_card(card)
    return card.id


def _set_review_order(col, value):
    conf = col.decks.config_dict_for_deck_id(1)
    conf["reviewOrder"] = value
    col.decks.update_config(conf)


def _queue_order(col):
    queued = col._backend.get_queued_cards(
        fetch_limit=10, intraday_learning_only=False
    )
    return [c.card.id for c in queued.cards]


def test_speedrun_points_at_stake_reorders_reviews():
    col = getEmptyCol()
    try:
        # A: more overdue but easy (0 lapses).
        # B: less overdue but maximally weak (8 lapses).
        a = _add_review_card(col, "A", overdue_days=10, interval=10, lapses=0)
        b = _add_review_card(col, "B", overdue_days=5, interval=10, lapses=8)

        # Baseline: relative overdueness studies the more-overdue card first.
        _set_review_order(col, REVIEW_ORDER_RELATIVE_OVERDUENESS)
        baseline = _queue_order(col)
        assert baseline.index(a) < baseline.index(b)

        # Points at stake weights B's weakness above A's extra urgency, so the
        # weaker card is promoted to the front. This difference proves our Rust
        # re-rank runs end to end (engine -> proto -> Python).
        _set_review_order(col, REVIEW_ORDER_SPEEDRUN_POINTS_AT_STAKE)
        speedrun = _queue_order(col)
        assert speedrun.index(b) < speedrun.index(a)

        assert baseline != speedrun
    finally:
        col.close()
