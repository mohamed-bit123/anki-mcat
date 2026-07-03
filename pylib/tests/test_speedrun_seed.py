# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""End-to-end test of the built-in MCAT flashcards and topic interleaving.

Proves that the shared Rust seeder (rslib/src/speedrun/seed.rs) creates the
built-in deck through the proto seam, and that the queue builder interleaves the
seeded cards across topics instead of blocking one subject at a time.
"""

from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV
from tests.shared import getEmptyCol

REVIEW_ORDER_SPEEDRUN_POINTS_AT_STAKE = 13


def _as_int(value):
    # generic.UInt32 may unwrap to an int or expose a `.val` field.
    return getattr(value, "val", value)


def test_speedrun_seed_is_idempotent():
    col = getEmptyCol()
    try:
        added = _as_int(col._backend.speedrun_seed_builtin())

        # The engine seeds both flashcards (MCAT::*) and questions (MCAT Practice::*).
        flashcards = col.find_cards("tag:mcat-flashcard")
        questions = col.find_cards("tag:mcat-question")
        assert len(flashcards) > 100, "expected a large flashcard bank"
        assert len(questions) > 50, "expected a large question bank"
        assert added == len(flashcards) + len(questions)
        assert len(col.find_cards("deck:MCAT::*")) == len(flashcards)
        assert len(col.find_cards('deck:"MCAT Practice::*"')) == len(questions)

        # Re-seeding adds nothing (idempotent).
        assert _as_int(col._backend.speedrun_seed_builtin()) == 0
    finally:
        col.close()


def test_speedrun_seeded_cards_interleave_topics():
    col = getEmptyCol()
    try:
        col._backend.speedrun_seed_builtin()

        # Turn the seeded new cards into due reviews so the points-at-stake queue
        # builder (which reranks reviews) runs on them.
        for i, cid in enumerate(col.find_cards("tag:mcat-flashcard")):
            card = col.get_card(cid)
            card.type = CARD_TYPE_REV
            card.queue = QUEUE_TYPE_REV
            card.due = col.sched.today - (i % 5)
            card.ivl = 10
            col.update_card(card)

        # The seeder already sets the MCAT deck to the interleaved order; confirm.
        mcat_did = col.decks.id("MCAT")
        conf = col.decks.config_dict_for_deck_id(mcat_did)
        assert conf["reviewOrder"] == REVIEW_ORDER_SPEEDRUN_POINTS_AT_STAKE

        col.decks.select(mcat_did)
        queued = col._backend.get_queued_cards(
            fetch_limit=60, intraday_learning_only=False
        )
        decks = [col.get_card(c.card.id).did for c in queued.cards]
        assert len(set(decks)) >= 5, "queue should span multiple topics"

        # With 7 topics of 8 cards each, greedy interleaving must alternate
        # topics for a long stretch: no two consecutive cards share a topic
        # across at least the first 14 cards (2 full rounds of 7 topics).
        window = decks[:14]
        consecutive_same = sum(1 for a, b in zip(window, window[1:]) if a == b)
        assert consecutive_same == 0, f"topics should interleave, got runs: {window}"
    finally:
        col.close()
