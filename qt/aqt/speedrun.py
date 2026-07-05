# Copyright: Ankitects Pty Ltd and contributors
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

from anki.cards import CardId
from anki.notes import Note
from aqt import speedrun_ai as ai
from aqt.qt import *
from aqt.utils import (
    disable_help_button,
    getText,
    restoreGeom,
    saveGeom,
    showInfo,
    showWarning,
    tooltip,
)

if TYPE_CHECKING:
    from aqt.main import AnkiQt

# These two tags are the seam with the engine seeder (rslib/src/speedrun/seed.rs):
# questions carry QUESTION_TAG, flashcards carry FLASHCARD_TAG. The notetype,
# fields, and decks are all created engine-side now, so the UI only needs the tags.
QUESTION_TAG = "mcat-question"
FLASHCARD_TAG = "mcat-flashcard"


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

        # Open-ended, one-question-at-a-time practice driven by concept-level
        # FSRS scheduling in the engine (speedrun_next_question).
        self.current_question: _Question | None = None
        self.session_count = 0
        self.session_correct = 0
        self.answered_today = 0
        self.rec_min = 0
        self.rec_max = 0
        self.answered = False
        self._generating = False

        self._build_ui()
        restoreGeom(self, "speedrun")
        self.refresh_scores()
        self._init_ai_mode()
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

        # AI mode switch + status indicator.
        ai_row = QHBoxLayout()
        ai_row.addWidget(QLabel("AI question generation:"))
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItem("Off — use the built-in bank only", ai.MODE_OFF)
        self.ai_mode_combo.addItem("Manual — generate when I click", ai.MODE_MANUAL)
        self.ai_mode_combo.addItem(
            "Auto — keep topics stocked (infinite)", ai.MODE_AUTO
        )
        self.ai_mode_combo.setToolTip(
            "Off: never calls the AI; the app works fully on the built-in bank.\n"
            "Manual: the “Generate with AI” button works, nothing runs on its own.\n"
            "Auto: also generates more in the background when a subject runs low, so "
            "practice never runs out."
        )
        self.ai_mode_combo.currentIndexChanged.connect(self._on_ai_mode_changed)
        ai_row.addWidget(self.ai_mode_combo)
        self.ai_status_label = QLabel("")
        self.ai_status_label.setTextFormat(Qt.TextFormat.RichText)
        ai_row.addWidget(self.ai_status_label)
        ai_row.addStretch(1)
        layout.addLayout(ai_row)

        # Practice area.
        self.daily_label = QLabel("")
        self.daily_label.setWordWrap(True)
        self.daily_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.daily_label)

        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)

        self.topic_label = QLabel("")
        self.topic_label.setStyleSheet("font-weight: bold; color: palette(mid);")
        layout.addWidget(self.topic_label)

        self.stem_label = QLabel("Start practice to begin.")
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
            # Stop Qt from styling the first answer as the dialog's "default"
            # button (macOS draws that highlighted, making A look pre-selected).
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.clicked.connect(lambda _checked=False, l=letter: self.on_answer(l))
            layout.addWidget(btn)
            self.option_buttons[letter] = btn

        self.dont_know_button = QPushButton("I don't know / I'm guessing")
        self.dont_know_button.setAutoDefault(False)
        self.dont_know_button.setDefault(False)
        self.dont_know_button.setToolTip(
            "Don't guess. If you're not sure, mark this instead of picking an answer. "
            "It counts as not known (like a wrong answer) and reveals the explanation, so a "
            "lucky guess can never inflate your Performance or Readiness."
        )
        self.dont_know_button.clicked.connect(self.on_dont_know)
        layout.addWidget(self.dont_know_button)

        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.feedback_label)

        self.next_button = QPushButton("Next question")
        self.next_button.clicked.connect(self.on_next)
        layout.addWidget(self.next_button)

        layout.addStretch(1)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start practice")
        self.start_button.setToolTip(
            "Open-ended practice: questions are served one at a time by "
            "concept-level FSRS scheduling (whichever concept is most due, "
            "weighted by MCAT yield). Go as long as you like — a recommended "
            "daily range is shown above."
        )
        self.start_button.clicked.connect(self.start_practice)
        controls.addWidget(self.start_button)

        self.test_button = QPushButton("Take timed test")
        self.test_button.setToolTip(
            "Sit a timed, exam-style block: pick a subject (or mixed) and a "
            "question count, answer under a clock with no feedback until the end, "
            "then get a scored summary. Every answered question still feeds your "
            "Performance and Readiness scores."
        )
        self.test_button.clicked.connect(self.on_take_test)
        controls.addWidget(self.test_button)

        self.setup_button = QPushButton("Set up MCAT content")
        self.setup_button.setToolTip(
            "Add the full built-in MCAT bank: flashcards (every subject) plus "
            "application questions, all from the shared engine. The MCAT deck is "
            "set to interleaved, weakness-weighted study. Idempotent."
        )
        self.setup_button.clicked.connect(self.on_setup_mcat)
        controls.addWidget(self.setup_button)

        self.generate_button = QPushButton("Generate with AI")
        self.generate_button.setToolTip(
            "Create fresh MCAT questions with AI, grounded in the built-in "
            "flashcards for a subject (so sources are traceable). New questions "
            "join the same bank and are scheduled and scored like any other — the "
            "bank effectively never runs out. Requires an OpenAI API key; the app "
            "works fully without it."
        )
        self.generate_button.clicked.connect(self.on_generate_ai)
        controls.addWidget(self.generate_button)

        self.calibrate_button = QPushButton("Record full-length score…")
        self.calibrate_button.setToolTip(
            "After you sit a real full-length practice test, log what the app "
            "projected vs. your actual scaled score. This calibrates Readiness: "
            "the range tightens to your real prediction error and, once "
            "calibrated, higher confidence can be reached. This is the "
            "“prove yourself wrong” honesty loop."
        )
        self.calibrate_button.clicked.connect(self.on_record_calibration)
        controls.addWidget(self.calibrate_button)

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

    def on_record_calibration(self) -> None:
        """Log a real full-length practice-test outcome to calibrate Readiness.

        Writes to the engine (`speedrun_record_calibration`), so the calibration
        rides collection config and syncs to the phone like every other score
        input. The projected field is pre-filled with the app's current
        Readiness projection so the common case is one edit + OK.
        """
        s = self.mw.col._backend.speedrun_scores()
        rdy = s.readiness
        projected_default = int(round(rdy.projected)) if rdy.known else 500

        dialog = QDialog(self)
        dialog.setWindowTitle("Record full-length practice score")
        disable_help_button(dialog)
        form = QFormLayout(dialog)

        blurb = QLabel(
            "After a real full-length practice test, log what the app projected "
            "at the time and the actual scaled score you got (both on the "
            "472–528 MCAT scale). This calibrates Readiness against reality: the "
            "range tightens to your true prediction error, and higher confidence "
            "becomes reachable."
        )
        blurb.setWordWrap(True)
        blurb.setMinimumWidth(360)
        form.addRow(blurb)

        projected_spin = QSpinBox()
        projected_spin.setRange(472, 528)
        projected_spin.setValue(projected_default)
        if rdy.known:
            projected_spin.setToolTip("Pre-filled with the app's current projection.")
        form.addRow("Projected (app's guess):", projected_spin)

        actual_spin = QSpinBox()
        actual_spin.setRange(472, 528)
        actual_spin.setValue(projected_default)
        form.addRow("Actual (your real score):", actual_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if not dialog.exec():
            return

        self.mw.col._backend.speedrun_record_calibration(
            projected=float(projected_spin.value()),
            actual=float(actual_spin.value()),
        )
        self.refresh_scores()
        tooltip("Recorded — Readiness recalibrated to your real score.", parent=self)

    # Practice flow (open-ended, one question at a time) ----------------------

    def _all_questions(self) -> list[_Question]:
        """Every application question in the bank, as `_Question` objects."""
        col = self.mw.col
        out: list[_Question] = []
        for nid in col.find_notes(f"tag:{QUESTION_TAG}"):
            note = col.get_note(nid)
            if "Stem" not in note or not note["Stem"]:
                continue
            card_ids = note.card_ids()
            if not card_ids:
                continue
            out.append(_Question(card_ids[0], note))
        return out

    def on_take_test(self) -> None:
        questions = self._all_questions()
        if not questions:
            showInfo(
                "No questions yet. Click “Set up MCAT content” to load the bank.",
                parent=self,
            )
            return
        setup = TestSetupDialog(self, questions)
        if not setup.exec():
            return
        config = setup.result_config()
        runner = TestRunnerDialog(self.mw, config, self)
        runner.exec()
        # Attempts logged during the test feed the engine; refresh the panel.
        self.refresh_scores()

    def start_practice(self) -> None:
        self.session_count = 0
        self.session_correct = 0
        self.next_button.setText("Next question")
        self.load_next_question()

    def load_next_question(self) -> None:
        col = self.mw.col
        resp = col._backend.speedrun_next_question()
        self.answered_today = resp.answered_today
        self.rec_min = resp.recommended_min
        self.rec_max = resp.recommended_max
        self._update_daily_label()
        if not resp.has_question:
            showInfo(
                "No application questions found. Click “Set up MCAT content” to load "
                "the built-in question bank, or import your own MCAT-style questions.",
                parent=self,
            )
            return
        try:
            card = col.get_card(CardId(resp.card_id))
        except Exception:
            self.stem_label.setText("Could not load the next question.")
            return
        self.current_question = _Question(resp.card_id, card.note())
        # "Why this surfaced": the concept's FSRS recall estimate.
        if resp.attempts == 0 and resp.concept_retrievability <= 0.0:
            why = "new concept"
        else:
            why = f"concept recall ≈ {resp.concept_retrievability * 100:.0f}%"
        self._show_current(why)
        self._maybe_autogen(self.current_question.topic)

    # AI generation -----------------------------------------------------------

    AUTOGEN_THRESHOLD = 3  # top up a topic when this few unseen questions remain
    AUTOGEN_BATCH = 5

    def _init_ai_mode(self) -> None:
        self._syncing_ai_mode = True
        idx = self.ai_mode_combo.findData(ai.get_mode(self.mw))
        self.ai_mode_combo.setCurrentIndex(max(0, idx))
        self._syncing_ai_mode = False
        self._update_ai_indicator()

    def _on_ai_mode_changed(self, _index: int) -> None:
        if getattr(self, "_syncing_ai_mode", False):
            return
        mode = self.ai_mode_combo.currentData()
        # Switching AI on needs a key; prompt once, or fall back to Off.
        if mode != ai.MODE_OFF and not ai.ai_available(self.mw):
            if not self._prompt_for_key():
                self._syncing_ai_mode = True
                self.ai_mode_combo.setCurrentIndex(
                    self.ai_mode_combo.findData(ai.MODE_OFF)
                )
                self._syncing_ai_mode = False
                mode = ai.MODE_OFF
        ai.set_mode(self.mw, mode)
        self._update_ai_indicator()
        self._update_practice_controls()

    def _update_ai_indicator(self) -> None:
        mode = ai.get_mode(self.mw)
        has_key = ai.ai_available(self.mw)
        if mode == ai.MODE_OFF:
            self.ai_status_label.setText(
                "<span style='color:palette(mid)'>● Off</span>"
            )
        elif not has_key:
            self.ai_status_label.setText(
                "<span style='color:#ef6c00'>● no API key set</span>"
            )
        elif mode == ai.MODE_AUTO:
            self.ai_status_label.setText(
                f"<span style='color:#2e7d32'>● On · auto · {ai.get_model(self.mw)}</span>"
            )
        else:
            self.ai_status_label.setText(
                f"<span style='color:#1565c0'>● On · manual · {ai.get_model(self.mw)}</span>"
            )

    def _maybe_autogen(self, topic: str) -> None:
        """When enabled, keep the served topic stocked so it never runs dry."""
        if self._generating or not topic:
            return
        if not ai.autogen_enabled(self.mw) or not ai.ai_available(self.mw):
            return
        try:
            if ai.unseen_count(self.mw.col, topic) > self.AUTOGEN_THRESHOLD:
                return
        except Exception:
            return
        self._run_generation(topic, self.AUTOGEN_BATCH, verify=False, quiet=True)

    def on_generate_ai(self) -> None:
        if not ai.available_topics(self.mw.col):
            showInfo(
                "Set up the MCAT content first — generation is grounded in the "
                "built-in flashcards for each subject.",
                parent=self,
            )
            return
        if not ai.ai_available(self.mw):
            if not self._prompt_for_key():
                return
        dialog = GenerateDialog(self, self.mw)
        if not dialog.exec():
            return
        cfg = dialog.result_config()
        self._run_generation(cfg["topic"], cfg["count"], verify=cfg["verify"])

    def _prompt_for_key(self) -> bool:
        key, ok = getText(
            "Paste your OpenAI API key (stored locally in this profile only, "
            "never in the project):",
            parent=self,
            title="OpenAI API key",
        )
        if not ok or not key.strip():
            return False
        ai.set_api_key(self.mw, key.strip())
        return True

    def _run_generation(
        self, topic: str, count: int, verify: bool, quiet: bool = False
    ) -> None:
        if self._generating:
            return
        col = self.mw.col
        facts = ai.source_facts(col, topic)
        avoid = ai.existing_stems(col, topic)
        self._generating = True

        def task() -> ai.GenerationResult:
            return ai.generate_questions(self.mw, topic, count, facts, avoid, verify)

        def on_done(future) -> None:
            self._generating = False
            try:
                result = future.result()
            except ai.AIError as e:
                if not quiet:
                    showWarning(str(e), parent=self, title="AI generation failed")
                return
            except Exception as e:  # pragma: no cover - defensive
                if not quiet:
                    showWarning(f"Unexpected error: {e}", parent=self)
                return
            try:
                added = ai.insert_questions(col, result)
            except ai.AIError as e:
                if not quiet:
                    showWarning(str(e), parent=self)
                return
            self.mw.reset()
            self._update_practice_controls()
            self.refresh_scores()
            if not quiet:
                msg = f"Added {added} AI question(s) for {topic}."
                if result.rejected:
                    msg += f" Rejected {result.rejected} (validation/verifier)."
                tooltip(msg, parent=self)

        label = f"Generating {count} {topic} question(s)…"
        self.mw.taskman.with_progress(task, on_done, parent=self, label=label)

    def _show_current(self, why: str) -> None:
        self.answered = False
        q = self.current_question
        assert q is not None
        self.progress_label.setText(
            f"This session: {self.session_count} answered  •  "
            f"{self.session_correct} correct"
        )
        self.topic_label.setText(f"{q.topic}  ·  {why}")
        self.stem_label.setText(q.stem)
        self.feedback_label.setText("")
        self.next_button.setEnabled(False)
        self.dont_know_button.setEnabled(True)
        for letter, btn in self.option_buttons.items():
            text = q.options.get(letter, "")
            btn.setText(f"{letter}.  {text}")
            btn.setEnabled(bool(text))
            btn.setStyleSheet("")

    def on_answer(self, letter: str) -> None:
        if self.answered or self.current_question is None:
            return
        self.answered = True
        q = self.current_question
        correct = letter == q.answer
        self.session_count += 1
        self.answered_today += 1
        if correct:
            self.session_correct += 1

        self.mw.col._backend.speedrun_record_attempt(card_id=q.card_id, correct=correct)

        self.dont_know_button.setEnabled(False)
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
        self.progress_label.setText(
            f"This session: {self.session_count} answered  •  "
            f"{self.session_correct} correct"
        )
        self.next_button.setEnabled(True)
        self._update_daily_label()
        self.refresh_scores()

    def on_dont_know(self) -> None:
        if self.answered or self.current_question is None:
            return
        self.answered = True
        q = self.current_question
        # An honest "I don't know" counts as not known (incorrect), so a lucky
        # guess can never inflate Performance/Readiness. Still reveal the answer.
        self.session_count += 1
        self.answered_today += 1
        self.mw.col._backend.speedrun_record_attempt(card_id=q.card_id, correct=False)

        self.dont_know_button.setEnabled(False)
        for opt_letter, btn in self.option_buttons.items():
            btn.setEnabled(False)
            if opt_letter == q.answer:
                btn.setStyleSheet("background-color: #cdebc5;")

        self.feedback_label.setText(
            "<b style='color:#ef6c00'>Marked “don’t know”.</b> Counts as not known, so guessing "
            f"can’t inflate your scores.<br>Answer: {q.answer}.<br>{q.explanation}"
        )
        self.progress_label.setText(
            f"This session: {self.session_count} answered  •  "
            f"{self.session_correct} correct"
        )
        self.next_button.setEnabled(True)
        self._update_daily_label()
        self.refresh_scores()

    def on_next(self) -> None:
        self.load_next_question()

    def _update_daily_label(self) -> None:
        done = self.answered_today
        lo, hi = self.rec_min, self.rec_max
        if lo and done < lo:
            nudge = f"— {lo - done} to today’s minimum"
            color = "palette(mid)"
        elif hi and done >= hi:
            nudge = "— daily max reached; more today has diminishing returns"
            color = "#c62828"
        else:
            nudge = "— minimum reached; keep going or stop anytime"
            color = "#2e7d32"
        self.daily_label.setText(
            f"<span style='color:{color}'>Today: {done} answered "
            f"(recommended {lo}–{hi}) {nudge}</span>"
        )

    def on_setup_mcat(self) -> None:
        added = self.mw.col._backend.speedrun_seed_builtin()
        added = getattr(added, "val", added)
        self.mw.reset()
        if added:
            cards = len(self.mw.col.find_notes(f"tag:{FLASHCARD_TAG}"))
            questions = len(self.mw.col.find_notes(f"tag:{QUESTION_TAG}"))
            showInfo(
                f"Set up the built-in MCAT bank: {cards} flashcards in the “MCAT” "
                f"deck and {questions} practice questions in “MCAT Practice”, across "
                "every subject. Studying the MCAT deck interleaves topics with the "
                "weakness-weighted points-at-stake order.",
                parent=self,
            )
        else:
            tooltip("MCAT content is already set up.", parent=self)
        self._update_practice_controls()
        self.refresh_scores()

    def _update_practice_controls(self) -> None:
        count = len(self.mw.col.find_notes(f"tag:{QUESTION_TAG}"))
        self.start_button.setEnabled(count > 0)
        self.test_button.setEnabled(count > 0)
        # AI generation is grounded in the built-in flashcards, so it needs the
        # content set up first, and only makes sense when AI isn't Off.
        has_flashcards = bool(self.mw.col.find_notes(f"tag:{FLASHCARD_TAG}"))
        self.generate_button.setEnabled(has_flashcards and ai.ai_on(self.mw))
        self._update_ai_indicator()
        if count == 0:
            self.stem_label.setText(
                "No application questions yet. Click “Set up MCAT content” to load "
                "the built-in bank."
            )
            self.daily_label.setText("")
        else:
            # Show today's pacing before the first question is drawn.
            resp = self.mw.col._backend.speedrun_next_question()
            self.answered_today = resp.answered_today
            self.rec_min = resp.recommended_min
            self.rec_max = resp.recommended_max
            self._update_daily_label()

    def reject(self) -> None:
        saveGeom(self, "speedrun")
        super().reject()

    def accept(self) -> None:
        saveGeom(self, "speedrun")
        super().accept()


class GenerateDialog(QDialog):
    """Configure an AI generation batch and (optionally) manage the key/model."""

    def __init__(self, parent: QDialog, mw: AnkiQt) -> None:
        super().__init__(parent)
        self.mw = mw
        self.setWindowTitle("Generate MCAT questions with AI")
        disable_help_button(self)
        self.resize(460, 0)

        layout = QVBoxLayout(self)
        blurb = QLabel(
            "Questions are <b>grounded in the built-in flashcards</b> for the "
            "chosen subject, so each one cites the source fact it tests. They join "
            "the same bank and are scheduled/scored like every other question."
        )
        blurb.setWordWrap(True)
        layout.addWidget(blurb)

        form = QFormLayout()
        self.topic_combo = QComboBox()
        for topic in ai.available_topics(mw.col):
            self.topic_combo.addItem(topic)
        form.addRow("Subject", self.topic_combo)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 25)
        self.count_spin.setValue(5)
        form.addRow("How many", self.count_spin)

        self.model_edit = QLineEdit(ai.get_model(mw))
        self.model_edit.setPlaceholderText(ai.DEFAULT_MODEL)
        form.addRow("Model", self.model_edit)

        self.key_edit = QLineEdit(ai.get_api_key(mw) or "")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-… (stored locally only)")
        form.addRow("API key", self.key_edit)
        layout.addLayout(form)

        self.verify_check = QCheckBox(
            "Double-check each question with an independent AI pass (slower, "
            "higher quality)"
        )
        self.verify_check.setChecked(True)
        layout.addWidget(self.verify_check)

        hint = QLabel(
            "Tip: set the panel’s AI mode to <b>Auto</b> to keep subjects stocked "
            "automatically during practice."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid); font-size: 11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Generate")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            showWarning("An OpenAI API key is required to generate.", parent=self)
            return
        ai.set_api_key(self.mw, key)
        ai.set_model(self.mw, self.model_edit.text().strip())
        self.accept()

    def result_config(self) -> dict:
        return {
            "topic": self.topic_combo.currentText(),
            "count": self.count_spin.value(),
            "verify": self.verify_check.isChecked(),
        }


class TestSetupDialog(QDialog):
    """Small form to configure a timed, exam-style block: subject scope, number
    of questions, and an optional countdown."""

    ALL_SUBJECTS = "All subjects (mixed)"

    def __init__(self, parent: QDialog, questions: list[_Question]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set up timed test")
        disable_help_button(self)
        self._questions = questions
        self._subjects = sorted({q.topic for q in questions if q.topic})

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Timed practice test</b>"))

        form = QFormLayout()
        self.scope_combo = QComboBox()
        self.scope_combo.addItem(f"{self.ALL_SUBJECTS} ({len(questions)})", None)
        for subject in self._subjects:
            n = sum(1 for q in questions if q.topic == subject)
            self.scope_combo.addItem(f"{subject} ({n})", subject)
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        form.addRow("Subject", self.scope_combo)

        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.valueChanged.connect(self._update_time_suggestion)
        form.addRow("Questions", self.count_spin)

        timed_row = QHBoxLayout()
        self.timed_check = QCheckBox("Timed")
        self.timed_check.setChecked(True)
        self.timed_check.toggled.connect(self._on_timed_toggled)
        timed_row.addWidget(self.timed_check)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(1, 600)
        timed_row.addWidget(self.minutes_spin)
        timed_row.addWidget(QLabel("minutes"))
        timed_row.addStretch(1)
        form.addRow("Time limit", timed_row)
        layout.addLayout(form)

        note = QLabel(
            "No feedback until you finish — just like a real section. Unanswered "
            "questions are scored as incorrect but are not logged against your "
            "Performance score."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: palette(mid); font-size: 11px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start test")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initialise counts/time for the default (all subjects) scope.
        self._on_scope_changed()

    def _current_pool(self) -> list[_Question]:
        subject = self.scope_combo.currentData()
        if subject is None:
            return list(self._questions)
        return [q for q in self._questions if q.topic == subject]

    def _on_scope_changed(self) -> None:
        pool_size = max(1, len(self._current_pool()))
        self.count_spin.setMaximum(pool_size)
        default = min(20, pool_size)
        self.count_spin.setValue(default)
        self._update_time_suggestion()

    def _on_timed_toggled(self, checked: bool) -> None:
        self.minutes_spin.setEnabled(checked)

    def _update_time_suggestion(self) -> None:
        # ~90 seconds per question is a realistic MCAT pace.
        self.minutes_spin.setValue(max(1, round(self.count_spin.value() * 1.5)))

    def result_config(self) -> dict:
        pool = self._current_pool()
        count = min(self.count_spin.value(), len(pool))
        subject = self.scope_combo.currentData()
        return {
            "pool": pool,
            "count": count,
            "timed": self.timed_check.isChecked(),
            "seconds": self.minutes_spin.value() * 60,
            "label": subject or self.ALL_SUBJECTS,
        }


class TestRunnerDialog(QDialog):
    """Runs a timed, exam-style block with no per-question feedback, then shows a
    scored summary and lets you review every question."""

    SELECTED_STYLE = "background-color: #cfe3f3;"

    def __init__(self, mw: AnkiQt, config: dict, parent: QDialog) -> None:
        super().__init__(parent)
        self.mw = mw
        self.setWindowTitle("MCAT timed test")
        disable_help_button(self)
        self.resize(680, 780)

        self.questions: list[_Question] = random.sample(config["pool"], config["count"])
        self.label: str = config["label"]
        self.answers: dict[int, str] = {}
        self.index = 0
        self.timed: bool = config["timed"]
        self.total_seconds: int = config["seconds"]
        self.remaining: int = config["seconds"]
        self._finished = False
        self.timer: QTimer | None = None

        self._build_ui()
        self._show_question()
        if self.timed:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._tick)
            self.timer.start(1000)
            self._update_timer_label()

    # UI ----------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Page 0: the test.
        test_page = QWidget()
        tp = QVBoxLayout(test_page)

        top = QHBoxLayout()
        self.progress_label = QLabel("")
        top.addWidget(self.progress_label)
        top.addStretch(1)
        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet("font-weight: bold;")
        top.addWidget(self.timer_label)
        tp.addLayout(top)

        self.topic_label = QLabel("")
        self.topic_label.setStyleSheet("font-weight: bold; color: palette(mid);")
        tp.addWidget(self.topic_label)

        self.stem_label = QLabel("")
        self.stem_label.setWordWrap(True)
        self.stem_label.setTextFormat(Qt.TextFormat.RichText)
        self.stem_label.setMinimumHeight(90)
        self.stem_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        tp.addWidget(self.stem_label)

        self.option_buttons: dict[str, QPushButton] = {}
        for letter in ("A", "B", "C", "D"):
            btn = QPushButton("")
            btn.setMinimumHeight(36)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.clicked.connect(lambda _checked=False, l=letter: self.on_select(l))
            tp.addWidget(btn)
            self.option_buttons[letter] = btn

        tp.addStretch(1)

        nav = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.on_prev)
        nav.addWidget(self.prev_button)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.on_next)
        nav.addWidget(self.next_button)
        nav.addStretch(1)
        self.finish_button = QPushButton("Finish test")
        self.finish_button.clicked.connect(lambda: self.finish(auto=False))
        nav.addWidget(self.finish_button)
        tp.addLayout(nav)

        self.stack.addWidget(test_page)

        # Page 1: the summary (built on finish).
        summary_page = QWidget()
        sp = QVBoxLayout(summary_page)
        self.summary_header = QLabel("")
        self.summary_header.setWordWrap(True)
        self.summary_header.setTextFormat(Qt.TextFormat.RichText)
        sp.addWidget(self.summary_header)
        self.review = QTextEdit()
        self.review.setReadOnly(True)
        sp.addWidget(self.review, 1)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("Done")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        sp.addLayout(close_row)
        self.stack.addWidget(summary_page)

    # Test flow ---------------------------------------------------------------

    def _show_question(self) -> None:
        q = self.questions[self.index]
        answered = len(self.answers)
        self.progress_label.setText(
            f"Question {self.index + 1} of {len(self.questions)}  •  "
            f"{answered} answered"
        )
        self.topic_label.setText(q.topic)
        self.stem_label.setText(q.stem)
        selected = self.answers.get(self.index)
        for letter, btn in self.option_buttons.items():
            text = q.options.get(letter, "")
            btn.setText(f"{letter}.  {text}")
            btn.setEnabled(bool(text))
            btn.setStyleSheet(self.SELECTED_STYLE if letter == selected else "")
        self.prev_button.setEnabled(self.index > 0)
        self.next_button.setText(
            "Next" if self.index < len(self.questions) - 1 else "Review answers"
        )

    def on_select(self, letter: str) -> None:
        self.answers[self.index] = letter
        for opt_letter, btn in self.option_buttons.items():
            btn.setStyleSheet(self.SELECTED_STYLE if opt_letter == letter else "")
        self.progress_label.setText(
            f"Question {self.index + 1} of {len(self.questions)}  •  "
            f"{len(self.answers)} answered"
        )

    def on_prev(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._show_question()

    def on_next(self) -> None:
        if self.index < len(self.questions) - 1:
            self.index += 1
            self._show_question()
        else:
            self.finish(auto=False)

    def _tick(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = 0
            self._update_timer_label()
            self.finish(auto=True)
            return
        self._update_timer_label()

    def _update_timer_label(self) -> None:
        if not self.timed:
            self.timer_label.setText("Untimed")
            return
        mins, secs = divmod(max(0, self.remaining), 60)
        color = "#c62828" if self.remaining <= 30 else "palette(text)"
        self.timer_label.setText(
            f"<span style='color:{color}'>Time left {mins:02d}:{secs:02d}</span>"
        )
        self.timer_label.setTextFormat(Qt.TextFormat.RichText)

    # Finish + summary --------------------------------------------------------

    def finish(self, auto: bool) -> None:
        if self._finished:
            return
        self._finished = True
        if self.timer is not None:
            self.timer.stop()

        correct = 0
        answered = 0
        by_subject: dict[str, list[int]] = {}
        for i, q in enumerate(self.questions):
            sel = self.answers.get(i)
            is_correct = sel is not None and sel == q.answer
            stats = by_subject.setdefault(q.topic or "—", [0, 0, 0])
            stats[2] += 1  # total in this subject
            if sel is not None:
                answered += 1
                stats[1] += 1  # answered
                # Only real attempts feed the engine's Performance/Readiness.
                self.mw.col._backend.speedrun_record_attempt(
                    card_id=q.card_id, correct=is_correct
                )
                if is_correct:
                    correct += 1
                    stats[0] += 1

        self._build_summary(correct, answered, by_subject, auto)
        self.stack.setCurrentIndex(1)

    def _build_summary(
        self,
        correct: int,
        answered: int,
        by_subject: dict[str, list[int]],
        auto: bool,
    ) -> None:
        total = len(self.questions)
        pct = (correct / total * 100) if total else 0.0
        blank = total - answered
        used = self.total_seconds - self.remaining if self.timed else None

        head = f"<h2>Test complete — {correct}/{total} correct ({pct:.0f}%)</h2>"
        parts = [f"Scope: {self.label}."]
        if blank:
            parts.append(f"{blank} left blank (scored incorrect).")
        if auto:
            parts.append("<b>Time expired.</b>")
        if used is not None:
            mins, secs = divmod(max(0, used), 60)
            parts.append(f"Time used: {mins:02d}:{secs:02d}.")
        subtitle = " ".join(parts)

        rows = []
        for subject in sorted(by_subject):
            c, a, t = by_subject[subject]
            sp = (c / t * 100) if t else 0.0
            rows.append(
                f"<tr><td>{subject}</td><td>&nbsp;{c}/{t}</td>"
                f"<td>&nbsp;{sp:.0f}%</td></tr>"
            )
        breakdown = (
            "<table><tr><th align='left'>Subject</th><th>Correct</th>"
            f"<th>&nbsp;%</th></tr>{''.join(rows)}</table>"
        )
        self.summary_header.setText(f"{head}<p>{subtitle}</p>{breakdown}")

        # Full review, so mistakes are learnable.
        blocks = []
        for i, q in enumerate(self.questions):
            sel = self.answers.get(i)
            correct_text = q.options.get(q.answer, "")
            if sel is None:
                verdict = "<span style='color:#c62828'>Left blank</span>"
                your = "—"
            elif sel == q.answer:
                verdict = "<span style='color:#2e7d32'>Correct</span>"
                your = f"{sel}. {q.options.get(sel, '')}"
            else:
                verdict = "<span style='color:#c62828'>Incorrect</span>"
                your = f"{sel}. {q.options.get(sel, '')}"
            blocks.append(
                f"<p><b>Q{i + 1} — {q.topic}</b> ({verdict})<br>"
                f"{q.stem}<br>"
                f"<b>Your answer:</b> {your}<br>"
                f"<b>Correct:</b> {q.answer}. {correct_text}<br>"
                f"<i>{q.explanation}</i></p><hr>"
            )
        self.review.setHtml("".join(blocks))

    def reject(self) -> None:
        # Closing mid-test: stop the clock; nothing is logged.
        if self.timer is not None:
            self.timer.stop()
        super().reject()


def show_speedrun(mw: AnkiQt) -> None:
    if not mw.col:
        return
    dialog = SpeedrunDialog(mw)
    dialog.show()
