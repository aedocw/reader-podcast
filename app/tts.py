"""Edge TTS synthesis: async parallel sentence synthesis with pydub combining."""

import asyncio
import logging
import os
import tempfile
import uuid

import edge_tts
import nltk
from pydub import AudioSegment

from app.config import MP3_DIR

log = logging.getLogger(__name__)

# Ensure punkt tokenizer is available
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

MAX_CONCURRENT = 10
MAX_RETRIES = 3
RETRY_BACKOFF_S = 3
PARAGRAPH_SILENCE_MS = 600


async def _synthesize_sentence(text, voice, output_path, semaphore):
    """Synthesize a single sentence to MP3 with retries."""
    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)
                return
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"TTS failed after {MAX_RETRIES} attempts for: {text[:60]!r}") from e
                log.warning("TTS attempt %d/%d failed: %s", attempt, MAX_RETRIES, e)
                await asyncio.sleep(RETRY_BACKOFF_S * attempt)


async def _synthesize_paragraph(sentences, voice, tmp_dir, semaphore):
    """Synthesize all sentences in a paragraph in parallel, return combined AudioSegment."""
    if not sentences:
        return AudioSegment.empty()

    # Create temp files and launch parallel synthesis
    tasks = []
    paths = []
    for i, sentence in enumerate(sentences):
        path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_{i}.mp3")
        paths.append(path)
        tasks.append(_synthesize_sentence(sentence, voice, path, semaphore))

    await asyncio.gather(*tasks)

    # Concatenate sentence audio in order
    combined = AudioSegment.empty()
    for path in paths:
        combined += AudioSegment.from_file(path, format="mp3")

    return combined


async def synthesize_paragraphs(paragraphs, voice, output_path):
    """Synthesize a list of paragraphs to a single MP3 file.

    Each paragraph is split into sentences, synthesized in parallel,
    then concatenated with silence between paragraphs.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    silence = AudioSegment.silent(duration=PARAGRAPH_SILENCE_MS)

    with tempfile.TemporaryDirectory(dir="data/tmp") as tmp_dir:
        final_audio = AudioSegment.empty()

        for i, paragraph in enumerate(paragraphs):
            sentences = nltk.sent_tokenize(paragraph)
            if not sentences:
                continue

            log.info("Paragraph %d/%d: %d sentences", i + 1, len(paragraphs), len(sentences))
            para_audio = await _synthesize_paragraph(sentences, voice, tmp_dir, semaphore)

            if len(final_audio) > 0:
                final_audio += silence
            final_audio += para_audio

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_audio.export(output_path, format="mp3")

    file_size = os.path.getsize(output_path)
    log.info("Wrote %s (%d bytes)", output_path, file_size)
    return file_size


def synthesize(paragraphs, voice, output_path):
    """Synchronous wrapper around synthesize_paragraphs."""
    return asyncio.run(synthesize_paragraphs(paragraphs, voice, output_path))
