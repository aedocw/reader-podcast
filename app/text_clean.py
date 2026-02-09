"""Text normalization for TTS input."""

import re


# Smart/curly quotes → straight
_QUOTE_MAP = str.maketrans({
    "\u2018": "'",  # left single
    "\u2019": "'",  # right single
    "\u201C": '"',  # left double
    "\u201D": '"',  # right double
    "\u2032": "'",  # prime
    "\u2033": '"',  # double prime
})

# Common dashes → standard hyphen/dash
_DASH_MAP = str.maketrans({
    "\u2013": "-",  # en dash
    "\u2014": " - ",  # em dash → spaced hyphen
    "\u2015": " - ",  # horizontal bar
})


def clean_text(text):
    """Normalize text for TTS: straighten quotes, collapse whitespace, clean punctuation."""
    # Straighten quotes and dashes
    text = text.translate(_QUOTE_MAP)
    text = text.translate(_DASH_MAP)

    # Replace ellipsis character with three dots
    text = text.replace("\u2026", "...")

    # Collapse multiple punctuation (e.g. "!!!" → "!", "..." stays as "...")
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)

    # Collapse multiple whitespace/newlines into single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_paragraphs(paragraphs):
    """Clean a list of paragraphs, dropping any that become empty."""
    cleaned = []
    for p in paragraphs:
        c = clean_text(p)
        if c:
            cleaned.append(c)
    return cleaned
