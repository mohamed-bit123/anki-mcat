# Brainlift — MCAT Speedrun

**Owner:** Mohamed Shawgi

> This is the project Brainlift: the learning-science thesis behind MCAT
> Speedrun and the evidence base for it. It follows the DOK (Depth of Knowledge)
> structure — Facts (DOK 1) → Summaries (DOK 2) → Insights (DOK 3) → Spiky POVs
> (DOK 4). The final section, **"From thesis to engine,"** maps each claim onto
> the exact code that implements it, so the research and the build are traceable
> to each other.

---

## Purpose

Build a desktop + mobile app (on Anki's codebase) that prepares premed
undergraduates for the MCAT. The app applies learning-science principles to
replace the dominant — and largely ineffective — MCAT study method (reread,
rewatch, highlight) with one that **decreases study time and improves scores**
by making study an act of _retrieval and application_ on a _spaced, interleaved_
schedule.

### In scope

- **Study methods.** Redefine _how_ the MCAT is studied for — not flashcards,
  videos, or textbook problem sets in isolation, but a learning-science-driven
  loop embedded in an app to raise efficiency, speed, and outcomes.
- **Integration of learning-science principles.** The core: expert findings on
  spacing, retrieval, interleaving, and cognitive load, and how they translate
  into software.
- **App development.** How those methods become an effective application —
  spaced repetition and cognitive-load management built into desktop + phone.

### Out of scope

- **Curriculum / subjects.** The MCAT already fixes the content outline. The app
  changes the _method_ of study, not _what_ is covered.
- **Replacing college.** Like any study tool, it complements coursework; it does
  not replace the classroom.

---

## DOK 4 — Spiky POVs (SPOVs)

1. **The bottleneck is memory _architecture_, not content volume.** The problem
   MCAT students face is not that there is too much to memorize — it is that the
   volume required for a good score cannot be held in an _unstable_ memory
   system. Anyone with a structured plan and enough disciplined effort can
   memorize the whole content base and score in (at least) the top 25%. The app's
   job is to build the stable architecture, not to trim the content.

2. **Mainstream MCAT study is misguided.** The research is overwhelming:
   retrieving and _applying_ prior learning — especially via practice testing —
   beats rereading, summarizing, or highlighting. Yet most students pour time
   into rereading texts and rewatching videos of already-covered topics instead
   of actively retrieving. An app built on **practice testing + constant
   retrieval practice + distributed spacing** can therefore deliver higher scores
   with less time and effort.

3. **Order review by memory strength, and interleave topics.** When reviewing,
   ordering topics by _how well you remember them_ beats chronological or
   textbook order. And **interleaving** questions across topics beats reviewing
   one topic at a time — particularly for the inductive reasoning the MCAT
   demands. So the app should **mix topics and order questions by the retrieval-
   and application-strength of their topics.** _(This SPOV is exactly the engine
   change — see "From thesis to engine.")_

---

## DOK 3 — Insights

**Distributed practice + interleaving + retrieval, combined.** The MCAT requires
a large body of content to be _readily retrievable_ under strict time limits.
The way to build that is a single combined loop:

> After a user first learns a topic comfortably, add it to a structure with a
> number representing its strength in the user's memory. Generate **daily review
> quizzes**. After a short delay, put the topic into a quiz through questions that
> require the user to **retrieve _and apply_** the knowledge (not just recognize
> it), then update the strength variable based on how well they did. The strength
> variable **decays over time** and drives _when_ the topic reappears, with
> **different topics interleaved** through the quiz.

That single structure fuses distributed practice, interleaving, and retrieval
practice — building the memory architecture needed to retrieve everything on
test day.

**Readiness = retrieval accessibility, not confidence or coverage.** Content
completion and _feelings_ of preparedness — how most students judge readiness —
are poor measures. **Retrieval accessibility is the best metric.** Note the
paradox: common methods raise _confidence_ without raising _outcomes_, while the
less-popular effective methods leave students feeling _less_ prepared yet produce
better delayed-test performance. An honest readiness score must therefore be
built on _demonstrated retrieval_, not self-report — and should be willing to
contradict the student's confidence.

**Critical thinking scales _with_ memorization, not against it.** Larger, more
accessible long-term memory enables _deeper_ critical thinking. Memory and
reasoning are complements, not counterforces — contrary to what schooling often
implies.

**Rereading only inflates retrieval strength temporarily.** Rereading a section
or rewatching a video raises _retrieval strength_ briefly while barely moving
_storage strength_. Retrieval strength then decays fast, and the next "restudy"
is nearly relearning from scratch — instead of _practicing retrieval_.

**The goal is to offload the exam onto long-term memory.** On test day, all
required information should already be in long-term memory, freeing scarce
working memory to select procedures, do quick calculations and inductive
reasoning (best trained by interleaving), answer, and move on. This is why so
many students run out of time: relying on working memory to re-derive facts is
far slower than retrieving them from long-term memory — a symptom of content that
was never properly committed to long-term storage.

---

## Knowledge Tree — sources, facts, summaries

### _Making Things Hard on Yourself, But in a Good Way_ (Bjork & Bjork)

**DOK 1 — Facts**

- Distributed practice improves delayed retention vs. massed practice.
- Interleaving improves delayed retention vs. blocked practice.
- Practice testing improves delayed retention vs. restudying.
- Varying learning conditions improves later recall and transfer.
- Retrieval strength and storage strength are separate properties of memory.
- Retrieval strength decreases over time if information is not revisited.
- Storage strength determines how resistant a memory is to forgetting.
- Difficult retrieval events increase storage strength more than easy ones.
- Conditions that improve immediate performance often fail to maximize long-term
  retention.

**DOK 2 — Summary.** Learning that feels too quick or easy is usually a bad
sign; effective learning feels hard in the moment. Interleaving, distributed
practice, and practice testing all _feel_ like less was learned yet reliably
raise delayed-test performance. There are **two** memory strengths: on test day
**retrieval strength** matters (how easily you pull information up), but
throughout studying **storage strength** should be optimized because it governs
how easily retrieval strength can be raised. _High storage + low retrieval →
high/high_ with a little practice; _high retrieval + low storage → low/low_
without constant practice.

### _Improving Students' Learning With Effective Learning Techniques_ (Dunlosky et al.)

**DOK 1 — Facts**

- Practice testing = **high**-utility technique.
- Distributed practice = **high**-utility technique.
- Summarization, highlighting, rereading, the keyword mnemonic = **low**-utility.
- Self-explanation, elaborative interrogation, interleaved practice = **promising
  but insufficiently evidenced** for broad recommendation.

**DOK 2 — Summary.** The two best-documented, most broadly effective techniques
are **distributed practice** and **practice testing**. Widely used methods —
summarization, highlighting, keyword mnemonic, rereading — are low-utility (don't
generalize across learners). Self-explanation, elaborative interrogation, and
interleaving look promising but need more evidence.

### _Why Don't Students Like School?_ (Willingham)

**DOK 1 — Facts**

- Working-memory capacity is highly limited.
- Long-term memory stores enormous amounts.
- Automatic retrieval reduces demands on working memory.
- Humans enjoy problems within an achievable difficulty band.
- Too-easy questions → boredom; too-hard → frustration.
- Successful problem solving produces intrinsic reward.

**DOK 2 — Summary.** Present new information with questions to keep learning
active, and calibrate difficulty so it is neither too hard nor too easy — the
"achievable challenge" band that yields intrinsic reward and keeps motivation
alive. Repeatedly encountering a fact/procedure makes it retrievable from
long-term memory, so precious working memory isn't spent re-deriving it.

### _Why Interleaving Enhances Inductive Learning_ (Kornell, Bjork, et al.)

**DOK 1 — Facts**

- Interleaving improves inductive learning and category discrimination.
- Interleaving highlights differences between categories; blocking hides them.
- **Excessive** alternation between categories _reduces_ interleaving's benefit.
- The _amount_ of interleaving matters, not just whether it occurs.

**DOK 2 — Summary.** Inductive learning = discovering general rules from specific
examples. Interleaving problems across topics helps inductive reasoning
(hypothesized: mixing exemplars highlights category differences). But it must be
done right: too-high alternation rates shrink the benefit, so **alternation
should be kept low.**

### _Test-Enhanced Learning_ (Roediger & Karpicke)

**DOK 1 — Facts**

- Testing improves future retention.
- Retrieval practice produces stronger long-term retention than restudying.
- Retrieval functions as both assessment _and_ learning.
- Successful retrieval strengthens future recall probability.

**DOK 2 — Summary.** The **testing effect**: taking a test both assesses and
_enhances_ later retention. "If students are tested on material and successfully
recall or recognize it, they will remember it better in the future than if they
had not been tested."

### _The Critical Role of Retrieval Practice in Long-Term Retention_ (Roediger & Karpicke)

**DOK 1 — Facts**

- Retrieval practice beats restudying.
- Retrieval should occur multiple times.
- Retrieval intervals should gradually increase.
- Retrieval is most effective once some forgetting has occurred.
- Errorless retrieval is desirable when possible.
- Difficult retrieval strengthens memory more than easy retrieval.

**DOK 2 — Summary.** Restates the value of retrieving over restudying.
**Errorless** retrieval is best, yet retrieval is also most effective when
somewhat **difficult** — balance the two with a schedule of multiple retrievals
at **increasing** delays (soon after learning, then longer, then longer still).

### _Spacing Effects in Learning: A Temporal Ridgeline of Optimal Retention_ (Cepeda et al.)

**DOK 1 — Facts**

- Spaced practice outperforms cramming for long-term retention.
- Increasing the interstudy gap first improves, then eventually reduces,
  retention.
- The optimal interstudy gap increases as the desired retention interval
  increases.
- The ideal spacing interval depends on time until the final test.

**DOK 2 — Summary.** Spaced practice beats cramming for durable retention. "At
any given test delay, an increase in the interstudy gap at first increased, and
then gradually reduced, final-test performance," and "the optimal gap increased
as test delay increased." (This paper studied single retrievals, not multi-
retrieval schedules.)

---

## Experts followed

| Expert                    | Role                                                                             | Why                                                                                                                                                           | Key work                                                                       |
| ------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **John Dunlosky**         | Prof. of Psychology, Kent State — self-regulated learning, metacognition         | Systematically ranks which study methods actually produce durable learning vs. an illusion of it — the strongest scientific case against mainstream MCAT prep | _Improving Students' Learning With Effective Learning Techniques_              |
| **Daniel T. Willingham**  | Prof. of Psychology, UVA — cognition→education translator                        | Explains why "critical thinking" is inseparable from accessible domain knowledge in long-term memory; reasoning is constrained by memory architecture         | danielwillingham.com; _Why Don't Students Like School?_, _Outsmart Your Brain_ |
| **Henry L. Roediger III** | Distinguished Univ. Prof., WashU — founder of modern retrieval-practice research | Shows retrieval is not just assessment but one of the most powerful _learning_ events; directly challenges reread/highlight/passive review                    | _Make It Stick_                                                                |
| **Jeffrey D. Karpicke**   | Prof. of Psychological Sciences, Purdue — retrieval-based learning               | Repeated retrieval substantially beats repeated study for long-term retention — central for a long-horizon exam like the MCAT                                 | Purdue profile; Google Scholar                                                 |
| **Robert A. Bjork**       | Distinguished Research Prof., UCLA                                               | Retrieval strength vs. storage strength + "desirable difficulties" — the core conceptual model of this Brainlift                                              | UCLA profile; work on desirable difficulties                                   |

---

## From thesis to engine — how the research is implemented

Every SPOV and insight above maps to concrete code. This is what makes the
Brainlift _load-bearing_ rather than decorative.

| Principle (source)                                                                                                                                        | Implementation                                                                                                                                                                                                                                                                                                                                                       | Where                                                                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Order review by memory strength × value; interleave topics, keep alternation low** (SPOV 3; Kornell/Bjork; Dunlosky)                                    | The **real Rust engine change**: `ReviewCardOrder::SpeedrunPointsAtStake` — due cards sorted by _topic weight × student weakness_ (points-at-stake), then **topic interleaving** so no two consecutive reviews share a subject while others remain                                                                                                                   | `rslib/src/speedrun/queue.rs`; write-up `speedrun/RUST-CHANGE.md`                                                                             |
| **Combined retrieval + spacing + interleaving loop; strength variable that decays and schedules reappearance** (DOK-3 insight; Cepeda; Roediger/Karpicke) | **Per-concept FSRS memory state** in `speedrunConcepts`; `speedrun_next_question` picks the most-_due_ concept (urgency = 1−R × MCAT yield, with a within-day rotation floor) then its least-recently-seen item; `speedrun_update_concept` advances/decays state on every attempt                                                                                    | `rslib/src/speedrun/concepts.rs`, `content.rs`                                                                                                |
| **Retrieval _and application_, not recognition** (SPOV 2; testing effect)                                                                                 | Open-ended, one-at-a-time **question runner** (not passive card flips); each attempt is graded and logged, feeding the concept state and the Performance score                                                                                                                                                                                                       | `qt/aqt/speedrun.py`, mobile `SpeedrunActivity.kt`, `content.rs::speedrun_record_attempt`                                                     |
| **Readiness = retrieval accessibility, not confidence/coverage; don't inflate** (DOK-3 insight; honesty rule)                                             | **Three separate scores** — Memory / Performance / Readiness — each with a range; **Readiness is refused** until there is applied-question evidence, so memorizing cards alone can never produce a readiness number                                                                                                                                                  | `rslib/src/speedrun/scores.rs`; `speedrun/models/`                                                                                            |
| **Retrieval strength vs. storage strength; high-retrieval/low-storage collapses without practice** (SPOV 1 & DOK-2; Bjork "desirable difficulties")       | Memory surfaces both: **retrieval strength now** (FSRS retrievability) and **storage strength** (mean FSRS stability, days). With a **target exam date**, retrievability is projected forward to that day; Readiness blends recall-now with projected recall and **widens the range by the durability gap**, so cramming projects lower and durable knowledge higher | `rslib/src/speedrun/queue.rs` (`card_retrievability_at`, `card_stability_days`), `scores.rs`, `content.rs` (exam date), `models/readiness.md` |
| **Difficulty calibrated to an achievable band** (Willingham)                                                                                              | Concept-urgency selection targets not-yet-mastered material with a recommended daily band (`RECOMMENDED_DAILY_MIN/_MAX`), avoiding both too-easy and overwhelming sessions                                                                                                                                                                                           | `rslib/src/speedrun/concepts.rs`                                                                                                              |
| **Coverage of the whole outline gates the score** (SPOV 1; MCAT breadth)                                                                                  | Performance is withheld until **every topic has ≥3 graded attempts**; Readiness reports **% of the official AAMC outline covered** and abstains below the line                                                                                                                                                                                                       | `scores.rs`; `verify/coverage_map.py`, `speedrun/mcat_outline.tsv`                                                                            |
| **Interleaving is a _hypothesis to test_, incl. its failure mode** (Kornell/Bjork: excess alternation hurts)                                              | Pre-registered study-feature test with **three builds** (full / interleaving-off ablation / plain Anki) at equal study time; null/negative results reported honestly                                                                                                                                                                                                 | `verify/ablation.py` → `verify/artifacts/ablation.md`                                                                                         |
| **Practice testing / high-utility techniques over low-utility ones** (Dunlosky)                                                                           | The entire product loop _is_ practice testing + distributed practice; no reread/highlight surface is built                                                                                                                                                                                                                                                           | whole app                                                                                                                                     |

### Deliberate design tensions (honesty)

- **Errorless vs. difficult retrieval** (Roediger/Karpicke conflict): resolved
  the way the research prescribes — schedule multiple retrievals at _increasing_
  delays (FSRS spacing) so retrieval is difficult-but-usually-successful, rather
  than forcing either extreme.
- **Interleaving can hurt at high alternation**: the engine keeps alternation
  low (interleave only enough to separate same-topic neighbors while preserving
  the highest-priority-first order), and the ablation is designed so "no
  difference / hurts here" is a valid, reportable outcome — not a failure to hide.
- **Memory strongly drives readiness** (Willingham/Roediger/Bjork) is our
  _model_; "show the range + evidence + the memory→performance gap" is the
  _presentation contract_. We still measure Performance separately (paraphrase
  test, `verify/paraphrase.py`) and report the gap honestly.

---

_See also: [`PLAN.md`](PLAN.md) (mission + locked decisions),
[`models/`](models/) (memory/performance/readiness one-pagers),
[`RUST-CHANGE.md`](RUST-CHANGE.md) (the engine change), and
[`../verify/`](../verify/README.md) (re-runnable evidence for every claim above)._
