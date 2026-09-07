"""Getting a screenshot's PIXELS to a model that can actually look at them.

## The gap this closes

`desktop_screenshot` returns a file path, which is the right answer for a
Claude or Cursor backend — those read the file with their own tools. An
`openai_api` backend has no file tools at all. Handing one a path is handing
it a string it can do nothing with, and the model's only honest reply is "I
cannot see it". So for those backends the image itself has to travel in the
conversation, as an `image_url` content part.

## Why a follow-up message rather than the tool result

The OpenAI tool protocol says a `tool` message's content is text. Images ride
on a `user` message. So after the tool result goes in, this appends one more
user message carrying the picture — which is also what makes the transcript
read correctly: the tool reported a capture, and then the picture arrived.

## Text-only models get told, not left guessing

A model without vision gets a sentence naming `desktop_ocr` instead. The
alternative — silence — produces a confident description of a screen nobody
looked at, which is the single worst outcome this whole feature can produce.

## Why there is nothing here for a CLI backend

Claude and Cursor already get the path in the tool result and open it with
their own file tools, which is the method that actually works on Windows where
pasting an image into a CLI does not. An "attach the path to the prompt"
helper was written for them and then deleted: it duplicated what the tool
result already said, and an unused function with a confident docstring is
worse than no function.

## Confinement

The path comes out of a tool result, which is model-influenced text. It is
resolved against the captures directory and refused if it escapes, so a
crafted result cannot turn into "read me any file and send it to the cloud".
"""

import base64
import fnmatch
import json
import mimetypes
import os

#: Only files under here can be attached. Not a general file-reading feature:
#: this exists to send back a picture the shell just took.
CAPTURE_DIR_REL = os.path.join("console", ".cache", "desktop-captures")

#: A data URL costs about 4/3 its bytes in base64, and every one of them stays
#: in the conversation for every later turn. 4 MB of PNG is already a large
#: screenshot; beyond that the cost outweighs the detail.
MAX_IMAGE_BYTES = 4 * 1024 * 1024

#: Tools whose results may carry a capture worth attaching.
CAPTURE_TOOLS = ("console_desktop_screenshot", "desktop-screenshot",
                 "mcp__console__desktop-screenshot")


def is_capture_tool(name):
    return (name or "") in CAPTURE_TOOLS


def is_vision_model(model, patterns):
    """Does `model` match any configured vision glob?

    Globs rather than a fixed list, because model ids move faster than this
    file does — `*vl*`, `gpt-4o*`, `claude*` keep working as versions change.
    An empty list means "assume not", which is the honest default: guessing
    yes produces a model asked to look at something it cannot see.
    """
    if not model or not patterns:
        return False
    name = model.lower()
    return any(fnmatch.fnmatch(name, str(p).lower()) for p in patterns)


def capture_path(result_text):
    """Pull the capture path out of a tool result, or None.

    Tolerant of shape: the result is JSON today, but a tool that returned a
    bare path should not silently stop working. Anything that is not a capture
    returns None and the caller does nothing.
    """
    if not result_text:
        return None
    text = result_text.strip()
    try:
        data = json.loads(text)
    except ValueError:
        return text if text.endswith(".png") else None
    if not isinstance(data, dict):
        return None
    if data.get("ok") is False:
        return None
    capture = data.get("capture")
    if isinstance(capture, dict) and capture.get("path"):
        return capture["path"]
    return data.get("path") if str(data.get("path", "")).endswith(".png") else None


def resolve_capture(repo_root, rel_path):
    """Absolute path of a capture, or None if it escapes the capture directory.

    The boundary, and the reason this function exists rather than an
    `os.path.join` at the call site.
    """
    if not rel_path:
        return None
    base = os.path.realpath(os.path.join(repo_root, CAPTURE_DIR_REL))
    candidate = os.path.realpath(os.path.join(repo_root, rel_path))
    if candidate != base and not candidate.startswith(base + os.sep):
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate


def data_url(path):
    """`data:image/png;base64,...` for a file already checked to be a capture."""
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) > MAX_IMAGE_BYTES:
        return None, ("the capture is %.1f MB, over the %.0f MB attachment cap"
                      % (len(raw) / 1e6, MAX_IMAGE_BYTES / 1e6))
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii")), ""


def after_capture(repo_root, tool_name, result_text, model, vision_patterns):
    """The extra message to append after a capture tool ran, or None.

    Returns an ordinary chat message dict, so the caller appends it and knows
    nothing about images.
    """
    if not is_capture_tool(tool_name):
        return None
    rel = capture_path(result_text)
    if not rel:
        return None

    if not is_vision_model(model, vision_patterns):
        # Told, not left to guess. A model that quietly describes a screen it
        # never saw is the worst outcome available here.
        return {
            "role": "user",
            "content": (
                "That capture was saved but this model cannot see images. "
                "Call desktop_ocr with the capture_id to read the text in it, "
                "and say plainly that you are working from OCR text rather "
                "than from the picture."
            ),
        }

    path = resolve_capture(repo_root, rel)
    if path is None:
        return {
            "role": "user",
            "content": ("That capture could not be attached: %r is not a file "
                        "in the captures directory." % rel),
        }

    url, problem = data_url(path)
    if url is None:
        return {
            "role": "user",
            "content": "That capture could not be attached: %s. Use desktop_ocr instead." % problem,
        }
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": "Here is the capture you just took."},
            {"type": "image_url", "image_url": {"url": url}},
        ],
    }
