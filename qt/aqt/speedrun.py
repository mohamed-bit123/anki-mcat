# Copyright: MCAT Speedrun fork
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Desktop UI for the MCAT Speedrun: a practice-question runner and a live,
honest three-score panel (Memory / Performance / Readiness).

The scores come straight from the Rust engine (`SpeedrunScores` RPC); this file
only renders them and feeds graded attempts back via `SpeedrunRecordAttempt`.
Application questions are notes of the "MCAT Practice Question" notetype tagged
``mcat-question`` so they stay separate from flashcards.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from anki.notes import Note
from aqt.qt import *
from aqt.utils import disable_help_button, restoreGeom, saveGeom, showInfo, tooltip

if TYPE_CHECKING:
    from aqt.main import AnkiQt

QUESTION_TAG = "mcat-question"
NOTETYPE_NAME = "MCAT Practice Question"
PRACTICE_DECK = "MCAT Practice"
FIELDS = ["Topic", "Stem", "A", "B", "C", "D", "Answer", "Explanation"]

# Original, hand-authored MCAT-style discrete questions used to seed the bank for
# a demo. (topic, stem, A, B, C, D, answer-letter, explanation)
SEED_QUESTIONS: list[tuple[str, str, str, str, str, str, str, str]] = [
    (
        "Biochemistry",
        "An enzyme follows Michaelis-Menten kinetics. A competitive inhibitor is added. "
        "How are Km and Vmax affected?",
        "Km increases, Vmax unchanged",
        "Km decreases, Vmax unchanged",
        "Km unchanged, Vmax decreases",
        "Km increases, Vmax decreases",
        "A",
        "Competitive inhibitors raise the apparent Km (more substrate needed) but Vmax is "
        "unchanged because high substrate outcompetes the inhibitor.",
    ),
    (
        "Biochemistry",
        "Which amino acid is most likely to be found buried in the hydrophobic core of a "
        "globular protein in aqueous solution?",
        "Lysine",
        "Glutamate",
        "Valine",
        "Serine",
        "C",
        "Valine has a nonpolar aliphatic side chain, so it preferentially partitions away from "
        "water into the protein core.",
    ),
    (
        "Biology",
        "During which phase of the cell cycle is DNA replicated?",
        "G1",
        "S",
        "G2",
        "M",
        "B",
        "DNA synthesis (replication) occurs during S phase, between the G1 and G2 gap phases.",
    ),
    (
        "Biology",
        "A nonsense mutation most directly results in which of the following?",
        "A silent change with no effect on the protein",
        "Substitution of one amino acid for another",
        "A premature stop codon and truncated protein",
        "A shift in the downstream reading frame",
        "C",
        "A nonsense mutation converts a codon into a stop codon, prematurely terminating "
        "translation and yielding a truncated protein.",
    ),
    (
        "General Chemistry",
        "What is the pH of a 0.001 M solution of HCl (a strong acid) at 25 degrees C?",
        "1",
        "3",
        "7",
        "11",
        "B",
        "HCl fully dissociates, so [H+] = 1e-3 M and pH = -log(1e-3) = 3.",
    ),
    (
        "General Chemistry",
        "Which quantum number determines the shape of an orbital?",
        "Principal (n)",
        "Azimuthal / angular momentum (l)",
        "Magnetic (m_l)",
        "Spin (m_s)",
        "B",
        "The azimuthal quantum number l defines the subshell and thus orbital shape "
        "(s, p, d, f).",
    ),
    (
        "Organic Chemistry",
        "An SN2 reaction proceeds fastest with which substrate?",
        "Tertiary alkyl halide",
        "Primary alkyl halide",
        "A bulky neopentyl halide",
        "An aryl halide",
        "B",
        "SN2 needs backside attack; primary substrates have the least steric hindrance, so they "
        "react fastest.",
    ),
    (
        "Physics",
        "A 2 kg object accelerates at 3 m/s^2. What net force acts on it?",
        "1.5 N",
        "5 N",
        "6 N",
        "9 N",
        "C",
        "By Newton's second law F = ma = 2 kg x 3 m/s^2 = 6 N.",
    ),
    (
        "Physics",
        "Light passes from air into glass (higher index of refraction). What happens to its "
        "speed and wavelength?",
        "Both increase",
        "Both decrease",
        "Speed decreases, wavelength unchanged",
        "Speed increases, wavelength decreases",
        "B",
        "In a denser medium light slows down and, since frequency is fixed, its wavelength "
        "decreases proportionally.",
    ),
    (
        "Psychology",
        "Classical conditioning was first systematically described by which researcher?",
        "B. F. Skinner",
        "Ivan Pavlov",
        "Jean Piaget",
        "Albert Bandura",
        "B",
        "Pavlov demonstrated classical conditioning through his experiments pairing a neutral "
        "stimulus with an unconditioned stimulus.",
    ),
    (
        "Psychology",
        "A drug that blocks reuptake of a neurotransmitter will most directly cause what at the "
        "synapse?",
        "Less neurotransmitter in the cleft",
        "More neurotransmitter remaining in the cleft",
        "Destruction of the postsynaptic receptor",
        "Reversal of the action potential",
        "B",
        "Blocking reuptake leaves more neurotransmitter in the synaptic cleft, prolonging its "
        "signaling.",
    ),
    (
        "Sociology",
        "A person changing their behavior because they know they are being observed exemplifies "
        "which effect?",
        "Hawthorne effect",
        "Halo effect",
        "Bystander effect",
        "Placebo effect",
        "A",
        "The Hawthorne effect is the alteration of behavior due to awareness of being observed.",
    ),
]


def ensure_notetype(col) -> dict:
    """Return the MCAT question notetype, creating it if needed."""
    existing = col.models.by_name(NOTETYPE_NAME)
    if existing:
        return existing
    mm = col.models
    nt = mm.new(NOTETYPE_NAME)
    for field_name in FIELDS:
        mm.add_field(nt, mm.new_field(field_name))
    template = mm.new_template("Card 1")
    template["qfmt"] = "{{Stem}}"
    template["afmt"] = "{{Answer}}. {{Explanation}}"
    mm.add_template(nt, template)
    mm.add(nt)
    return mm.by_name(NOTETYPE_NAME)


def seed_demo_questions(col) -> int:
    """Add the hand-authored demo questions. Returns the number added.

    Each question goes in a per-topic subdeck (``MCAT Practice::<Topic>``) because
    the engine treats the deck as the question's topic; this makes the
    weakness-weighted ordering differentiate topics instead of lumping them.
    """
    nt = ensure_notetype(col)
    added = 0
    for topic, stem, a, b, c, d, answer, explanation in SEED_QUESTIONS:
        deck_id = col.decks.id(f"{PRACTICE_DECK}::{topic}")
        note = col.new_note(nt)
        note["Topic"] = topic
        note["Stem"] = stem
        note["A"] = a
        note["B"] = b
        note["C"] = c
        note["D"] = d
        note["Answer"] = answer
        note["Explanation"] = explanation
        note.tags.append(QUESTION_TAG)
        col.add_note(note, deck_id)
        added += 1
    return added


class _Question:
    def __init__(self, card_id: int, note: Note):
        self.card_id = card_id
        self.topic = note["Topic"] if "Topic" in note else ""
        self.stem = note["Stem"]
        self.options = {k: note[k] for k in ("A", "B", "C", "D") if k in note}
        self.answer = (note["Answer"] if "Answer" in note else "").strip().upper()[:1]
        self.explanation = note["Explanation"] if "Explanation" in note else ""


class SpeedrunDialog(QDialog):
    def __init__(self, mw: AnkiQt) -> None:
        super().__init__(mw)
        self.mw = mw
        self.setWindowTitle("MCAT Speedrun")
        disable_help_button(self)
        self.resize(640, 720)

        self.questions: list[_Question] = []
        self.priority_by_card: dict[int, float] = {}
        self.index = 0
        self.correct_count = 0
        self.answered = False

        self._build_ui()
        restoreGeom(self, "speedrun")
        self.refresh_scores()
        self._update_practice_controls()

    # UI construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("<h2>MCAT Speedrun</h2>")
        layout.addWidget(header)

        # Three score cards.
        scores_row = QHBoxLayout()
        self.memory_label = self._score_card(scores_row, "Memory")
        self.performance_label = self._score_card(scores_row, "Performance")
        self.readiness_label = self._score_card(scores_row, "Readiness")
        layout.addLayout(scores_row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        # Practice area.
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)

        self.topic_label = QLabel("")
        self.topic_label.setStyleSheet("font-weight: bold; color: palette(mid);")
        layout.addWidget(self.topic_label)

        self.stem_label = QLabel("Start a practice set to begin.")
        self.stem_label.setWordWrap(True)
        self.stem_label.setTextFormat(Qt.TextFormat.RichText)
        self.stem_label.setMinimumHeight(80)
        self.stem_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self.stem_label)

        self.option_buttons: dict[str, QPushButton] = {}
        for letter in ("A", "B", "C", "D"):
            btn = QPushButton("")
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda _checked=False, l=letter: self.on_answer(l))
            layout.addWidget(btn)
            self.option_buttons[letter] = btn

        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.feedback_label)

        self.next_button = QPushButton("Next question")
        self.next_button.clicked.connect(self.on_next)
        layout.addWidget(self.next_button)

        layout.addStretch(1)

        # Bottom controls.
        self.weighted_check = QCheckBox(
            "Weakness-weighted order (points at stake)"
        )
        self.weighted_check.setChecked(True)
        self.weighted_check.setToolTip(
            "On: the engine ranks questions by topic points x weakness x need "
            "(unseen / recently missed / stale first), the question analogue of "
            "the points-at-stake review queue.\nOff: plain random order."
        )
        layout.addWidget(self.weighted_check)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start practice set")
        self.start_button.clicked.connect(self.start_set)
        controls.addWidget(self.start_button)

        self.seed_button = QPushButton("Seed demo questions")
        self.seed_button.clicked.connect(self.on_seed)
        controls.addWidget(self.seed_button)

        controls.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)

    def _score_card(self, row: QHBoxLayout, title: str) -> QLabel:
        box = QGroupBox(title)
        box_layout = QVBoxLayout(box)
        label = QLabel("—")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setMinimumHeight(96)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        box_layout.addWidget(label)
        row.addWidget(box, 1)
        return label

    # Scores ------------------------------------------------------------------

    def refresh_scores(self) -> None:
        s = self.mw.col._backend.speedrun_scores()

        mem = s.memory
        if mem.known:
            self.memory_label.setText(
                f"<h3>{mem.value:.0f}<span style='font-size:11px'>/100</span></h3>"
                f"<span style='font-size:11px'>retained over {mem.studied_cards} studied "
                f"card(s)<br>{mem.topic_coverage * 100:.0f}% of topics covered</span>"
            )
        else:
            self.memory_label.setText(
                f"<h3 style='color:palette(mid)'>—</h3>"
                f"<span style='font-size:11px'>{mem.reason}</span>"
            )

        perf = s.performance
        if perf.known:
            self.performance_label.setText(
                f"<h3>{perf.value:.0f}<span style='font-size:11px'>/100</span></h3>"
                f"<span style='font-size:11px'>applied accuracy over {perf.attempts} "
                f"question(s)<br>{perf.topics_covered} topic(s)</span>"
            )
        else:
            self.performance_label.setText(
                f"<h3 style='color:palette(mid)'>—</h3>"
                f"<span style='font-size:11px'>{perf.reason}</span>"
            )

        rdy = s.readiness
        if rdy.known:
            self.readiness_label.setText(
                f"<h3>{rdy.projected:.0f}</h3>"
                f"<span style='font-size:11px'>range {rdy.low:.0f}–{rdy.high:.0f} "
                f"(472–528 scale)<br>{rdy.confidence} confidence<br>{rdy.calibration_note}"
                f"</span>"
            )
        else:
            self.readiness_label.setText(
                f"<h3 style='color:palette(mid)'>—</h3>"
                f"<span style='font-size:11px'>{rdy.reason}</span>"
            )

    # Practice flow -----------------------------------------------------------

    def _load_questions_random(self) -> list[_Question]:
        col = self.mw.col
        questions: list[_Question] = []
        for nid in col.find_notes(f"tag:{QUESTION_TAG}"):
            note = col.get_note(nid)
            if "Stem" not in note or not note["Stem"]:
                continue
            card_ids = note.card_ids()
            if not card_ids:
                continue
            questions.append(_Question(card_ids[0], note))
        random.shuffle(questions)
        return questions

    def _load_questions_weighted(self) -> list[_Question]:
        """Order from the engine's points-at-stake question ranking."""
        col = self.mw.col
        # Single-field responses are auto-unwrapped, so this is the repeated list.
        resp = col._backend.speedrun_next_questions()
        questions: list[_Question] = []
        self.priority_by_card = {}
        for item in resp:
            try:
                card = col.get_card(item.card_id)
            except Exception:
                continue
            note = card.note()
            if "Stem" not in note or not note["Stem"]:
                continue
            questions.append(_Question(item.card_id, note))
            self.priority_by_card[item.card_id] = item.priority
        return questions

    def start_set(self) -> None:
        self.priority_by_card = {}
        if self.weighted_check.isChecked():
            self.questions = self._load_questions_weighted()
        else:
            self.questions = self._load_questions_random()
        if not self.questions:
            showInfo(
                "No application questions found. Click “Seed demo questions” to add a "
                "starter set, or import your own MCAT-style questions.",
                parent=self,
            )
            return
        self.index = 0
        self.correct_count = 0
        self.show_question()

    def show_question(self) -> None:
        self.answered = False
        q = self.questions[self.index]
        extra = ""
        if self.weighted_check.isChecked():
            priority = self.priority_by_card.get(q.card_id)
            if priority is not None:
                extra = f"  •  points-at-stake priority {priority:.2f}"
        self.progress_label.setText(
            f"Question {self.index + 1} of {len(self.questions)}  •  "
            f"{self.correct_count} correct so far{extra}"
        )
        self.topic_label.setText(q.topic)
        self.stem_label.setText(q.stem)
        self.feedback_label.setText("")
        self.next_button.setEnabled(False)
        for letter, btn in self.option_buttons.items():
            text = q.options.get(letter, "")
            btn.setText(f"{letter}.  {text}")
            btn.setEnabled(bool(text))
            btn.setStyleSheet("")

    def on_answer(self, letter: str) -> None:
        if self.answered:
            return
        self.answered = True
        q = self.questions[self.index]
        correct = letter == q.answer
        if correct:
            self.correct_count += 1

        self.mw.col._backend.speedrun_record_attempt(
            card_id=q.card_id, correct=correct
        )

        for opt_letter, btn in self.option_buttons.items():
            btn.setEnabled(False)
            if opt_letter == q.answer:
                btn.setStyleSheet("background-color: #cdebc5;")
            elif opt_letter == letter and not correct:
                btn.setStyleSheet("background-color: #f3c9c9;")

        verdict = (
            "<b style='color:#2e7d32'>Correct.</b>"
            if correct
            else f"<b style='color:#c62828'>Incorrect.</b> Answer: {q.answer}."
        )
        self.feedback_label.setText(f"{verdict}<br>{q.explanation}")
        self.next_button.setEnabled(True)
        self.refresh_scores()

    def on_next(self) -> None:
        self.index += 1
        if self.index >= len(self.questions):
            tooltip(
                f"Set complete: {self.correct_count}/{len(self.questions)} correct.",
                parent=self,
            )
            self._finish_set()
            return
        self.show_question()

    def _finish_set(self) -> None:
        self.progress_label.setText(
            f"Set complete: {self.correct_count}/{len(self.questions)} correct."
        )
        self.topic_label.setText("")
        self.stem_label.setText("Start another practice set to keep going.")
        self.feedback_label.setText("")
        self.next_button.setEnabled(False)
        for btn in self.option_buttons.values():
            btn.setText("")
            btn.setEnabled(False)
            btn.setStyleSheet("")
        self.refresh_scores()

    def on_seed(self) -> None:
        existing = len(self.mw.col.find_notes(f"tag:{QUESTION_TAG}"))
        if existing:
            showInfo(
                f"You already have {existing} application question(s). "
                "Seeding is only needed on an empty bank.",
                parent=self,
            )
            return
        added = seed_demo_questions(self.mw.col)
        tooltip(f"Added {added} demo questions.", parent=self)
        self._update_practice_controls()

    def _update_practice_controls(self) -> None:
        count = len(self.mw.col.find_notes(f"tag:{QUESTION_TAG}"))
        self.start_button.setEnabled(count > 0)
        if count == 0:
            self.stem_label.setText(
                "No application questions yet. Click “Seed demo questions” to add a "
                "starter set."
            )

    def reject(self) -> None:
        saveGeom(self, "speedrun")
        super().reject()

    def accept(self) -> None:
        saveGeom(self, "speedrun")
        super().accept()


def show_speedrun(mw: AnkiQt) -> None:
    if not mw.col:
        return
    dialog = SpeedrunDialog(mw)
    dialog.show()
