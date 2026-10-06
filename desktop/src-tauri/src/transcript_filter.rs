//! Junk filter for transcripts: sound tags and silence hallucinations.
//!
//! The speech engine narrates the room when there is no speech: "[BLANK_AUDIO]",
//! "(machinery whirring)", "*coughs*", "♪ la ♪", and on pure silence it
//! answers "you" or "Thank you.". None of that was said to the assistant, so
//! it must not reach the gate, the console or the Sent cue.
//!
//! Pure: no audio, no I/O, no logging. The caller logs the reason and a word
//! count, never the text. A hand-written scanner rather than a regex (no new
//! crate for a small job, and it lets a tag that holds a digit be kept).

/// Why a transcript was thrown away. Only its name is ever logged.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Dropped {
    /// Nothing but tags and punctuation was left ("[Music]", "...", "[").
    NoWords,
    /// Exactly one of the engine's known silence hallucinations.
    Hallucination,
}

impl Dropped {
    pub fn name(self) -> &'static str {
        match self {
            Dropped::NoWords => "sound tag or punctuation only",
            Dropped::Hallucination => "known silence hallucination",
        }
    }
}

/// Whole-transcript matches (lower case) that mean "no speech". The tag forms
/// "[blank_audio]" and "(silence)" are already removed by the scanner.
const HALLUCINATIONS: &[&str] = &[
    "thank you.",
    "thanks for watching!",
    "thank you for watching.",
    "you",
    "bye.",
];

/// The cleaned transcript, or why it is not worth acting on.
pub fn clean(text: &str) -> Result<String, Dropped> {
    let stripped = strip_tags(text);
    let cleaned = stripped.split_whitespace().collect::<Vec<_>>().join(" ");
    if !cleaned.chars().any(char::is_alphanumeric) {
        return Err(Dropped::NoWords);
    }
    if HALLUCINATIONS.contains(&cleaned.to_lowercase().as_str()) {
        return Err(Dropped::Hallucination);
    }
    Ok(cleaned)
}

/// Replace every `[..]`, `(..)`, `*..*` and `♪..♪` span with a space. `[`, `(`
/// and `♪` may be left unclosed (they run to the end); a lone `*` is a plain
/// character. A span holding a digit ("(T-002)") is somebody's words, so it
/// stays.
fn strip_tags(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some((at, open)) = rest.char_indices().find(|(_, c)| matches!(c, '[' | '(' | '*' | '♪')) {
        out.push_str(&rest[..at]);
        let after = &rest[at + open.len_utf8()..];
        let close = match open {
            '[' => ']',
            '(' => ')',
            '*' => '*',
            _ => '♪',
        };
        let (inner, tail, closed) = match after.find(close) {
            Some(i) => (&after[..i], &after[i + close.len_utf8()..], true),
            None => (after, "", false),
        };
        if open == '*' && !closed {
            out.push('*');
            rest = after;
            continue;
        }
        if inner.chars().any(|c| c.is_ascii_digit()) {
            out.push_str(&rest[at..rest.len() - tail.len()]);
        } else {
            out.push(' ');
        }
        rest = tail;
    }
    out.push_str(rest);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn kept(text: &str) -> Option<String> {
        clean(text).ok()
    }

    /// AC-10: the table, verbatim.
    #[test]
    fn the_ac_10_table() {
        for junk in [
            "[BLANK_AUDIO]",
            "(music)",
            "*coughs*",
            "♪ la ♪",
            "...",
            "[",
            "Thank you.",
            "you",
        ] {
            assert!(clean(junk).is_err(), "{junk:?} should be dropped");
        }
        assert_eq!(kept("[Music] open T-002").as_deref(), Some("open T-002"));
        assert_eq!(kept("(T-002) status").as_deref(), Some("(T-002) status"));
        assert_eq!(
            kept("thank you for the summary").as_deref(),
            Some("thank you for the summary")
        );
    }

    #[test]
    fn the_listed_hallucinations_are_dropped_in_any_case_and_spacing() {
        for h in [
            "Thank you.",
            "THANK YOU.",
            "  thanks   for watching!  ",
            "Thank you for watching.",
            "You",
            "Bye.",
            "[blank_audio]",
            "(silence)",
        ] {
            assert!(clean(h).is_err(), "{h:?}");
        }
        // Only an exact match: the same words inside a request survive.
        assert_eq!(kept("thank you very much").as_deref(), Some("thank you very much"));
    }

    #[test]
    fn the_reason_tells_a_tag_from_a_hallucination() {
        assert_eq!(clean("(machinery whirring)"), Err(Dropped::NoWords));
        assert_eq!(clean("(clippers whirring)"), Err(Dropped::NoWords));
        assert_eq!(clean("..."), Err(Dropped::NoWords));
        assert_eq!(clean(""), Err(Dropped::NoWords));
        assert_eq!(clean("Thank you."), Err(Dropped::Hallucination));
        assert_eq!(clean("you"), Err(Dropped::Hallucination));
        assert_eq!(clean("[Music] you"), Err(Dropped::Hallucination));
    }

    #[test]
    fn tags_are_removed_wherever_they_sit_and_unclosed_ones_run_to_the_end() {
        assert_eq!(kept("open [pause] the tickets").as_deref(), Some("open the tickets"));
        assert_eq!(kept("show me *coughs* the tickets").as_deref(), Some("show me the tickets"));
        assert_eq!(kept("♪ la la ♪ status").as_deref(), Some("status"));
        assert_eq!(kept("status (background noise").as_deref(), Some("status"));
        assert_eq!(kept("status [BLANK_AUDIO").as_deref(), Some("status"));
        assert_eq!(kept("status ♪ humming").as_deref(), Some("status"));
        assert_eq!(kept("(a) (b) status").as_deref(), Some("status"));
    }

    #[test]
    fn a_lone_star_is_a_character_and_a_span_with_a_digit_is_words() {
        assert_eq!(kept("2 * 3 is six").as_deref(), Some("2 * 3 is six"));
        assert_eq!(kept("a * b").as_deref(), Some("a * b"));
        assert_eq!(kept("[ticket 2] now").as_deref(), Some("[ticket 2] now"));
        assert_eq!(kept("(T-002)").as_deref(), Some("(T-002)"));
        assert_eq!(kept("status (T-002").as_deref(), Some("status (T-002"));
    }

    #[test]
    fn whitespace_collapses_and_accented_or_digit_text_counts_as_words() {
        assert_eq!(kept("  open \t the\n tickets  ").as_deref(), Some("open the tickets"));
        assert_eq!(kept("café").as_deref(), Some("café"));
        assert_eq!(kept("42").as_deref(), Some("42"));
        assert_eq!(clean("?!").err(), Some(Dropped::NoWords));
    }
}
