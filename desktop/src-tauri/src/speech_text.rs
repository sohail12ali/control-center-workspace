//! Turning a written reply into something worth listening to.
//!
//! ## Why this exists
//!
//! A model writes for a screen: `**bold**`, bullet lists, fenced code, links
//! with URLs in them, `T-002`. A synthesiser reads what it is given. The
//! result is the single biggest reason a spoken reply sounds like a machine —
//! not the voice, the *text*. Before this, `speak()` was handed the reply
//! verbatim.
//!
//! ## The rules, and what each is protecting against
//!
//! - **Code fences are dropped, not read.** Nobody wants forty lines of Rust
//!   spelled out, and there is no reading of `let mut x = 0;` that sounds
//!   like speech. The listener is told a block was skipped, so the reply does
//!   not silently lose a limb.
//! - **Emphasis markers, headers and list bullets go.** They are typography.
//!   A list still reads as a list because the items keep their sentence
//!   breaks.
//! - **Links become their text.** "Click [the plan](https://…/T-010-plan.md)"
//!   is one word of use and forty characters of noise.
//! - **Ticket ids become how a person says them.** `T-010` read literally is
//!   "tee dash zero one zero". A person says "tee ten".
//! - **Tables are skipped.** A table read aloud, cell by cell with pipes, is
//!   the clearest possible demonstration of why this module exists.
//!
//! Everything here is pure and tested. The rules are opinions, and opinions
//! are better argued with in a test file than in a synthesiser.

/// Cap on what will be spoken in one go. A model can produce pages; reading
/// pages aloud is not a feature, it is a hostage situation. The console
/// already trims to its own `reply_chars`, and this is the backstop.
pub const MAX_CHARS: usize = 2000;

/// The written reply, as it should be said.
pub fn spoken_form(text: &str) -> String {
    let stripped = strip_markup(text);
    truncate(&stripped)
}

/// Markdown out, prose in.
fn strip_markup(text: &str) -> String {
    let mut out: Vec<String> = Vec::new();
    let mut in_fence = false;
    let mut dropped_code = false;

    for raw in text.lines() {
        let line = raw.trim_end();
        let trimmed = line.trim_start();

        if trimmed.starts_with("```") || trimmed.starts_with("~~~") {
            in_fence = !in_fence;
            if in_fence {
                dropped_code = true;
            }
            continue;
        }
        if in_fence {
            continue;
        }
        // A table row, or the `|---|---|` rule under it.
        if trimmed.starts_with('|') && trimmed.ends_with('|') {
            continue;
        }
        // A horizontal rule is a visual device with nothing to say.
        if trimmed.len() >= 3 && trimmed.chars().all(|c| c == '-' || c == '=' || c == '*') {
            continue;
        }

        let mut line = trimmed.to_string();
        // Headers: the text is worth speaking, the hashes are not.
        line = line.trim_start_matches('#').trim_start().to_string();
        // Blockquote markers.
        line = line.trim_start_matches('>').trim_start().to_string();
        // List markers. The line keeps its own sentence, so a list still
        // reads as a sequence rather than as one run-on.
        line = strip_list_marker(&line);
        line = links_to_text(&line);
        line = drop_emphasis(&line);
        line = say_ticket_ids(&line);
        line = bare_urls_to_words(&line);

        let line = line.trim().to_string();
        if !line.is_empty() {
            out.push(line);
        }
    }

    let mut body = join_sentences(&out);
    if dropped_code {
        // Said, not silently swallowed: a reply whose whole answer was a code
        // block would otherwise be spoken as nothing at all.
        if body.is_empty() {
            body = "There's a code block in the reply — it's on screen.".into();
        } else {
            body.push_str(" There's code in the reply, on screen.");
        }
    }
    body
}

/// `- item`, `* item`, `1. item`, `1) item` -> `item`.
fn strip_list_marker(line: &str) -> String {
    let rest = line.trim_start();
    for marker in ["- ", "* ", "+ "] {
        if let Some(tail) = rest.strip_prefix(marker) {
            return tail.to_string();
        }
    }
    // A numbered item: digits then `.` or `)` then a space.
    let digits: String = rest.chars().take_while(char::is_ascii_digit).collect();
    if !digits.is_empty() && digits.len() <= 3 {
        let after = &rest[digits.len()..];
        for marker in [". ", ") "] {
            if let Some(tail) = after.strip_prefix(marker) {
                return tail.to_string();
            }
        }
    }
    rest.to_string()
}

/// `[text](url)` -> `text`.
fn links_to_text(line: &str) -> String {
    let mut out = String::with_capacity(line.len());
    let chars: Vec<char> = line.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '[' {
            if let Some(close) = find_from(&chars, i + 1, ']') {
                // Only a real link: `](` has to follow.
                if chars.get(close + 1) == Some(&'(') {
                    if let Some(end) = find_from(&chars, close + 2, ')') {
                        out.extend(&chars[i + 1..close]);
                        i = end + 1;
                        continue;
                    }
                }
            }
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

fn find_from(chars: &[char], from: usize, want: char) -> Option<usize> {
    chars.iter().skip(from).position(|c| *c == want).map(|p| p + from)
}

/// Emphasis and inline code markers. The words between them stay.
fn drop_emphasis(line: &str) -> String {
    let mut out = String::with_capacity(line.len());
    for c in line.chars() {
        match c {
            // Underscores only matter as emphasis around words; inside an
            // identifier like `max_tool_rounds` they are how it is spelled,
            // and a synthesiser handles that better than "max tool rounds"
            // arriving as three words with no relation.
            '*' | '`' | '~' => continue,
            c => out.push(c),
        }
    }
    out
}

/// `T-002` -> `T 2`, `CC-T001` -> `CC-T 1`.
///
/// Read literally these come out as "tee dash zero zero two", which is nobody's
/// idea of how to say a ticket number. A person says "tee two".
///
/// The letters must be UPPERCASE, which is what keeps `pre-2020` a word and
/// `T-002` an id — the two are otherwise the same shape, and this workspace's
/// ids are uppercase by convention (`consolidate`'s naming rule).
fn say_ticket_ids(line: &str) -> String {
    let chars: Vec<char> = line.chars().collect();
    let mut out = String::with_capacity(line.len());
    let mut i = 0;
    while i < chars.len() {
        let start = i;
        let starts_clean = start == 0 || !chars[start - 1].is_ascii_alphanumeric();
        if starts_clean && chars[start].is_ascii_uppercase() {
            // The letter part, which may itself carry a dash: `CC-T`.
            let mut j = start;
            while j < chars.len()
                && (chars[j].is_ascii_uppercase() || chars[j] == '-')
                && j - start < 8
            {
                j += 1;
            }
            let mut k = j;
            while k < chars.len() && chars[k].is_ascii_digit() {
                k += 1;
            }
            let has_digits = k > j;
            let prefix: String =
                chars[start..j].iter().collect::<String>().trim_end_matches('-').to_string();
            // A trailing letter-run with no digits is just a word in capitals.
            if has_digits && !prefix.is_empty() && prefix.chars().any(|c| c.is_ascii_uppercase()) {
                let digits: String = chars[j..k].iter().collect();
                let number = digits.trim_start_matches('0');
                out.push_str(&prefix);
                out.push(' ');
                out.push_str(if number.is_empty() { "0" } else { number });
                i = k;
                continue;
            }
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

/// A bare URL is unspeakable. Say that there is one.
fn bare_urls_to_words(line: &str) -> String {
    line.split_whitespace()
        .map(|word| {
            if word.starts_with("http://") || word.starts_with("https://") {
                "a link"
            } else {
                word
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Join the surviving lines into flowing speech.
///
/// A line that already ends a sentence just runs on; one that does not gets a
/// full stop, which is what turns a bullet list into a sequence of statements
/// instead of one breathless clause.
fn join_sentences(lines: &[String]) -> String {
    let mut out = String::new();
    for line in lines {
        if !out.is_empty() {
            out.push(' ');
        }
        out.push_str(line);
        if !line.ends_with(['.', '!', '?', ':', ';', ',']) {
            out.push('.');
        }
    }
    out
}

fn truncate(text: &str) -> String {
    let trimmed = text.trim();
    if trimmed.chars().count() <= MAX_CHARS {
        return trimmed.to_string();
    }
    let cut: String = trimmed.chars().take(MAX_CHARS).collect();
    // Break at a sentence end if there is one nearby, so it does not stop
    // mid-word.
    match cut.rfind(['.', '!', '?']) {
        Some(idx) if idx > MAX_CHARS / 2 => cut[..=idx].to_string(),
        _ => cut,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn emphasis_and_code_markers_are_not_read_out() {
        assert_eq!(spoken_form("**Two** tickets are `open`."),
                   "Two tickets are open.");
    }

    #[test]
    fn a_bullet_list_becomes_sentences() {
        // The point: a list should sound like a list, not like one sentence
        // with the word "dash" in it four times.
        let out = spoken_form("Open now:\n- T-010 voice work\n- T-002 the tray\n");
        assert_eq!(out, "Open now: T 10 voice work. T 2 the tray.");
    }

    #[test]
    fn a_numbered_list_loses_its_numbers_but_keeps_its_items() {
        let out = spoken_form("1. first thing\n2) second thing");
        assert_eq!(out, "first thing. second thing.");
    }

    #[test]
    fn headers_keep_their_words() {
        assert_eq!(spoken_form("## What is open\nTwo tickets."),
                   "What is open. Two tickets.");
    }

    #[test]
    fn a_code_block_is_skipped_and_said_to_have_been() {
        // Silently dropping it would leave a reply that answers nothing;
        // reading it would be worse.
        let out = spoken_form("Run this:\n```bash\ncargo test --all\n```\nThat's it.");
        assert!(!out.contains("cargo"), "{out}");
        assert!(out.contains("code"), "the listener must know something was skipped: {out}");
    }

    #[test]
    fn a_reply_that_is_only_code_still_says_something() {
        let out = spoken_form("```\nlet x = 1;\n```");
        assert!(!out.is_empty());
        assert!(out.contains("code"));
    }

    #[test]
    fn a_link_becomes_its_text() {
        assert_eq!(spoken_form("See [the plan](https://example.com/T-010-plan.md) first."),
                   "See the plan first.");
    }

    #[test]
    fn a_bare_url_is_not_spelled_out() {
        let out = spoken_form("Open https://console.local/agents to see it.");
        assert_eq!(out, "Open a link to see it.");
    }

    #[test]
    fn a_table_is_skipped_entirely() {
        let out = spoken_form("Status:\n| id | lane |\n|---|---|\n| T-010 | done |\nThat's all.");
        assert_eq!(out, "Status: That's all.");
    }

    #[test]
    fn ticket_ids_are_said_the_way_people_say_them() {
        assert_eq!(spoken_form("T-002 is in verify"), "T 2 is in verify.");
        assert_eq!(spoken_form("T-010 and CC-T001"), "T 10 and CC-T 1.");
    }

    #[test]
    fn a_hyphenated_word_is_not_mistaken_for_a_ticket() {
        // `pre-2020` is a word, not an id, and the difference is whether the
        // letters are attached to something else.
        let out = spoken_form("a pre-2020 build");
        assert_eq!(out, "a pre-2020 build.");
    }

    #[test]
    fn an_underscored_identifier_is_left_alone() {
        // `max_tool_rounds` spelled with the underscores intact is read
        // better by every synthesiser than three unrelated words.
        assert!(spoken_form("set max_tool_rounds").contains("max_tool_rounds"));
    }

    #[test]
    fn plain_prose_is_untouched_apart_from_trimming() {
        let text = "Two tickets are open right now, and one is nearly done.";
        assert_eq!(spoken_form(text), text);
    }

    #[test]
    fn a_long_reply_is_trimmed_at_a_sentence_end() {
        let long = "word. ".repeat(1000);
        let out = spoken_form(&long);
        assert!(out.chars().count() <= MAX_CHARS);
        assert!(out.ends_with('.'));
    }

    #[test]
    fn a_long_reply_with_no_sentence_end_is_still_capped() {
        let out = spoken_form(&"y".repeat(5000));
        assert_eq!(out.chars().count(), MAX_CHARS);
    }

    #[test]
    fn empty_in_empty_out() {
        assert_eq!(spoken_form("   \n\n  "), "");
    }
}
