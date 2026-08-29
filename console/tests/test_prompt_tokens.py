"""Inline `/skill`, `@agent` and `#file` references.

Two things are being defended here and they pull in opposite directions.

**Prose must survive.** People write "and/or", "see issue #1234" and email
addresses in chat messages. A composer that mangles those is worse than one
with no tokens at all, because the damage is silent — the agent answers a
question nobody asked.

**A reference must not reach somewhere it shouldn't.** `#` names a file, files
are read by the agent, and `.env` holds every credential this console
authenticates with. The picker and the resolver both refuse what `agent_tools`
refuses, so the two can never drift apart.
"""

import os

import pytest

from server import agent_backends, prompt_tokens as pt


@pytest.fixture
def workspace(repo):
    """A root with a small but real .claude roster and a couple of files."""
    def touch(rel, body="x"):
        path = os.path.join(repo, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)

    touch(".claude/skills/plan/SKILL.md", "# plan")
    touch(".claude/skills/verify/SKILL.md", "# verify")
    touch(".claude/agents/builder.md", "# builder")
    touch("src/app.py", "print()")
    touch("src/notes.md", "notes")
    touch(".env", "SECRET_KEY=hunter2")
    touch("config/.env", "OTHER=1")
    os.makedirs(os.path.join(repo, "src", "deep"), exist_ok=True)
    return repo


def wire(workspace, text, style="slash", **kw):
    return pt.compose(workspace, text, style, **kw)[0]


def report(workspace, text, style="slash", **kw):
    return pt.compose(workspace, text, style, **kw)[1]


# ----------------------------------------------------------------- syntax --
class TestScanning:
    """Purely syntactic; no disk. Boundaries only."""

    def test_a_token_must_start_the_input_or_follow_whitespace(self):
        assert [t.name for t in pt.scan("/plan at start")] == ["plan"]
        assert [t.name for t in pt.scan("go /plan now")] == ["plan"]

    def test_a_slash_inside_a_word_is_not_a_token(self):
        # "and/or", "24/7", "TCP/IP" — ordinary prose, and by far the most
        # common way a naive matcher ruins a message.
        assert pt.scan("and/or 24/7 TCP/IP") == []

    def test_an_email_address_is_not_a_persona(self):
        assert pt.scan("mail sohail@hu-manity.co about it") == []

    def test_a_markdown_heading_is_not_a_file(self):
        # `# Heading` and `## Notes` both fail the "name starts alphanumeric"
        # rule, which is exactly why that rule is there.
        assert pt.scan("# Heading\n\n## Notes") == []

    def test_a_bare_trigger_is_not_a_token(self):
        assert pt.scan("/ @ #") == []

    def test_tokens_are_capped(self):
        text = " ".join("#f%d" % i for i in range(pt.MAX_TOKENS + 25))
        assert len(pt.scan(text)) == pt.MAX_TOKENS


# --------------------------------------------------------------- resolving --
class TestOnlyRealThingsResolve:
    """A token that names nothing real stays as typed. That is what makes
    prose safe without an escaping rule anybody has to learn."""

    def test_a_real_skill_resolves(self, workspace):
        assert report(workspace, "run /plan now")["skills"] == ["plan"]

    def test_an_unknown_skill_does_not(self, workspace):
        rep = report(workspace, "run /nosuchskill now")
        assert rep["skills"] == [] and rep["unresolved"] == ["/nosuchskill"]

    def test_a_real_persona_resolves(self, workspace):
        assert report(workspace, "ask @builder")["personas"] == ["builder"]

    def test_a_real_path_resolves(self, workspace):
        assert report(workspace, "read #src/app.py")["paths"] == ["src/app.py"]

    def test_an_issue_number_is_not_a_path(self, workspace):
        # "#1234" is syntactically a token and semantically not a file. It
        # survives as text because no such path exists.
        rep = report(workspace, "see issue #1234")
        assert rep["paths"] == [] and rep["unresolved"] == ["#1234"]

    def test_an_unresolved_token_is_left_verbatim(self, workspace):
        text = "check /nope and #alsonope"
        assert wire(workspace, text) == text

    def test_a_directory_resolves(self, workspace):
        # Pointing an agent at a folder is a perfectly good instruction.
        assert report(workspace, "look in #src/deep")["paths"] == ["src/deep"]


class TestSecretPathsAreRefused:
    def test_a_dotenv_reached_by_traversal_does_not_resolve(self, workspace):
        rep = report(workspace, "read #config/../.env")
        assert rep["paths"] == []

    def test_a_nested_dotenv_does_not_resolve(self, workspace):
        assert report(workspace, "read #config/.env")["paths"] == []

    def test_a_path_outside_the_workspace_does_not_resolve(self, workspace):
        assert report(workspace, "read #../../../etc/passwd")["paths"] == []

    def test_the_secret_list_is_agent_tools_own(self):
        # Shared rather than copied: a pattern added for the tools must apply
        # to the picker too, or the picker offers what the tools refuse.
        from server import agent_tools
        assert pt.is_secret(".env")
        assert agent_tools.SECRET_PATTERNS
        for pattern in ("id_rsa", "x.pem", "credentials.json"):
            assert pt.is_secret(pattern), pattern
        assert not pt.is_secret("notes.md")


# --------------------------------------------------------------- rendering --
class TestSlashStyle:
    """claude parses `/skill` and `@agent` itself. Only `#path` is rewritten."""

    def test_skills_and_personas_are_left_alone(self, workspace):
        assert wire(workspace, "/plan @builder go") == "/plan @builder go"

    def test_a_file_becomes_claudes_own_at_form(self, workspace):
        assert wire(workspace, "read #src/app.py") == "read @src/app.py"

    def test_an_unresolved_file_is_not_rewritten(self, workspace):
        assert wire(workspace, "read #nope.py") == "read #nope.py"


class TestNamedStyles:
    """cursor-agent and an API model have no command syntax, so a reference
    has to become words."""

    @pytest.mark.parametrize("style", ["inline", "none"])
    def test_a_skill_becomes_a_sentence_naming_its_file(self, workspace, style):
        out = wire(workspace, "run /plan", style)
        assert ".claude/skills/plan/SKILL.md" in out

    @pytest.mark.parametrize("style", ["inline", "none"])
    def test_a_persona_becomes_a_sentence_naming_its_file(self, workspace, style):
        out = wire(workspace, "ask @builder", style)
        assert ".claude/agents/builder.md" in out

    @pytest.mark.parametrize("style", ["inline", "none"])
    def test_the_users_own_wording_survives(self, workspace, style):
        # The preamble is prepended, not woven in. An agent reading a mangled
        # sentence answers the mangled version.
        out = wire(workspace, "please run /plan carefully", style)
        assert "please run plan carefully" in out

    def test_a_file_is_named_and_never_inlined(self, workspace, style="none"):
        # The prompt budget is 24k chars and one file can exceed it alone.
        # The agent has read_file; naming the path costs a dozen tokens.
        out = wire(workspace, "read #src/app.py", style)
        assert "src/app.py" in out
        assert "print()" not in out   # the file's CONTENT must not appear


class TestExplicitSelectionsStillWork:
    """The dropdowns are a statement about the whole chat; a token is a
    reference inside one message. Both apply."""

    def test_slash_style_prefixes_the_dropdown_choices(self, workspace):
        out = wire(workspace, "go", "slash", skill="plan", persona="builder")
        assert out == "@builder /plan go"

    def test_inline_style_names_the_files(self, workspace):
        out = wire(workspace, "go", "inline", skill="plan")
        assert ".claude/skills/plan/SKILL.md" in out and out.endswith("go")

    def test_none_style_leaves_the_dropdowns_to_prompt_build(self, workspace):
        # For an API backend the skill is INJECTED into the system prompt by
        # prompt_build, so repeating it in the message would pay for it twice.
        assert wire(workspace, "go", "none", skill="plan") == "go"

    def test_both_a_dropdown_and_a_token_can_apply(self, workspace):
        out = wire(workspace, "also /verify", "slash", skill="plan")
        assert "/plan" in out and "/verify" in out

    def test_a_selection_the_text_already_names_is_not_repeated(self, workspace):
        """Choosing `plan` AND typing `/plan` used to send "/plan /plan go".

        For a slash backend the explicit selection is prepended as the very
        same token the text already carries, so the two routes to naming a
        skill collided. They now converge: whichever route named it, it is
        named once.
        """
        out = wire(workspace, "/plan go", "slash", skill="plan")
        assert out.count("/plan") == 1, out

    def test_deduping_is_per_name_not_all_or_nothing(self, workspace):
        # A skill named in the text and a persona chosen in the form are two
        # different statements; silencing the persona too would drop one.
        out = wire(workspace, "/plan go", "slash", skill="plan", persona="builder")
        assert out.count("/plan") == 1 and "@builder" in out, out

    def test_an_unresolved_lookalike_does_not_silence_the_selection(self, workspace):
        # `/plna` is a typo, so it resolves to nothing and travels as prose.
        # The real selection must still apply — otherwise a typo would quietly
        # disable the skill the user actually chose.
        out = wire(workspace, "/plna go", "slash", skill="plan")
        assert out.startswith("/plan ") and "/plna" in out, out


class TestNoWorkspace:
    """Without a root there is no roster, so tokens stay as typed and only the
    dropdowns apply — the behaviour this function had before tokens existed."""

    def test_tokens_are_untouched(self):
        assert pt.compose(None, "run /plan", "slash")[0] == "run /plan"

    def test_dropdowns_still_apply(self):
        assert pt.compose(None, "go", "slash", persona="builder")[0] == "@builder go"


class TestBackendDelegation:
    """`Backend.compose_prompt` is the seam every caller uses."""

    def _backend(self, style):
        return agent_backends.Backend({"id": "b", "command": "x",
                                       "transport": "oneshot",
                                       "prompt_prefix_style": style})

    def test_it_resolves_tokens_when_given_a_root(self, workspace):
        out = self._backend("slash").compose_prompt("read #src/app.py",
                                                    repo_root=workspace)
        assert out == "read @src/app.py"

    def test_it_is_inert_without_one(self, workspace):
        out = self._backend("slash").compose_prompt("read #src/app.py")
        assert out == "read #src/app.py"


# ------------------------------------------------------------ file search --
class TestFileSearch:
    def test_it_finds_by_substring(self, workspace):
        hits = {h["path"] for h in pt.search_files(workspace, "app")}
        assert "src/app.py" in hits

    def test_it_never_offers_a_secret(self, workspace):
        # The one that matters. Offering .env would be a menu item whose only
        # outcome is the agent's tools refusing it — after the path is on
        # screen and possibly in a transcript.
        for query in ("", "env", ".env"):
            paths = [h["path"] for h in pt.search_files(workspace, query, 50)]
            assert not any(p.endswith(".env") for p in paths), query

    def test_directories_are_offered_with_a_trailing_slash(self, workspace):
        hits = {h["path"]: h["kind"] for h in pt.search_files(workspace, "deep")}
        assert hits.get("src/deep/") == "dir"

    def test_a_filename_match_outranks_a_directory_match(self, workspace):
        # Typing "app" should surface app.py, not everything under a folder
        # that happens to contain the letters.
        hits = pt.search_files(workspace, "app")
        assert hits[0]["path"] == "src/app.py"

    def test_the_limit_is_honoured(self, workspace):
        assert len(pt.search_files(workspace, "", 3)) <= 3

    def test_skipped_directories_stay_skipped(self, workspace):
        os.makedirs(os.path.join(workspace, "node_modules", "pkg"), exist_ok=True)
        with open(os.path.join(workspace, "node_modules", "pkg", "index.js"),
                  "w", encoding="utf-8") as fh:
            fh.write("//")
        paths = [h["path"] for h in pt.search_files(workspace, "index", 50)]
        assert not any("node_modules" in p for p in paths)
