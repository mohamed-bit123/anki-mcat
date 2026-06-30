// Copyright: MCAT Speedrun fork
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Speedrun (MCAT fork) engine extensions.
//!
//! New logic for the MCAT study app lives in dedicated submodules so it stays
//! easy to reason about and to merge against upstream Anki. The first real
//! engine change is the weakness-weighted "points at stake" review ordering in
//! [`queue`].

pub mod content;
pub mod queue;
pub mod scores;
