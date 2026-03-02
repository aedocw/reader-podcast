"""VibeVoice TTS synthesis with Whisper audio quality verification.

Requires:
    pip install git+https://github.com/microsoft/VibeVoice.git
    pip install torch openai-whisper thefuzz

Voice files (.pt) are loaded from the VibeVoice package's demo/voices/streaming_model/
directory, or from ~/repos/VibeVoice/demo/voices/streaming_model/ as a fallback.
"""

import copy
import logging
import os
import re
import tempfile

from pydub import AudioSegment

from app.config import MP3_DIR

log = logging.getLogger(__name__)

MODEL_PATH = "microsoft/VibeVoice-Realtime-0.5B"
SPEAKER_NAME = "Davis"
MIN_RATIO = 88
MAX_RETRIES = 3
PARAGRAPH_SILENCE_MS = 600

# Lazy-loaded singletons
_model = None
_processor = None
_prefilled_outputs = None
_device = None
_whisper_model = None


def _get_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _get_voice_path(speaker_name):
    import vibevoice
    vibevoice_dir = os.path.dirname(vibevoice.__file__)
    voices_dir = os.path.join(os.path.dirname(vibevoice_dir), "demo", "voices", "streaming_model")

    if not os.path.exists(voices_dir):
        voices_dir = os.path.expanduser("~/repos/VibeVoice/demo/voices/streaming_model")

    if not os.path.exists(voices_dir):
        raise FileNotFoundError(
            f"VibeVoice voices directory not found at {voices_dir}.\n"
            "Install VibeVoice from GitHub: "
            "pip install git+https://github.com/microsoft/VibeVoice.git"
        )

    pt_files = [f for f in os.listdir(voices_dir) if f.endswith(".pt")]
    if not pt_files:
        raise FileNotFoundError(f"No .pt voice files found in {voices_dir}")

    for pt_file in pt_files:
        name = os.path.splitext(pt_file)[0]
        if speaker_name.lower() == name.lower() or speaker_name.lower() in name.lower():
            log.info("Found voice file: %s", pt_file)
            return os.path.join(voices_dir, pt_file)

    log.warning("Voice '%s' not found, using %s", speaker_name, pt_files[0])
    return os.path.join(voices_dir, pt_files[0])


def _load_model():
    global _model, _processor, _prefilled_outputs, _device
    if _model is not None:
        return

    import torch
    from vibevoice.modular.modeling_vibevoice_streaming_inference import (
        VibeVoiceStreamingForConditionalGenerationInference,
    )
    from vibevoice.processor.vibevoice_streaming_processor import VibeVoiceStreamingProcessor

    _device = _get_device()
    log.info("Loading VibeVoice model on %s", _device)

    _processor = VibeVoiceStreamingProcessor.from_pretrained(MODEL_PATH)

    if _device == "mps":
        load_dtype = torch.float32
        attn_impl = "sdpa"
    elif _device == "cuda":
        load_dtype = torch.bfloat16
        attn_impl = "flash_attention_2"
    else:
        load_dtype = torch.float32
        attn_impl = "sdpa"

    try:
        if _device == "mps":
            _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                MODEL_PATH,
                torch_dtype=load_dtype,
                attn_implementation=attn_impl,
                device_map=None,
            )
            _model.to("mps")
        else:
            _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                MODEL_PATH,
                torch_dtype=load_dtype,
                device_map=_device,
                attn_implementation=attn_impl,
            )
    except Exception as e:
        if attn_impl == "flash_attention_2":
            log.warning("flash_attention_2 failed (%s), retrying with sdpa", e)
            _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                MODEL_PATH,
                torch_dtype=load_dtype,
                device_map=_device,
                attn_implementation="sdpa",
            )
        else:
            raise

    _model.eval()
    _model.set_ddpm_inference_steps(num_steps=5)

    voice_path = _get_voice_path(SPEAKER_NAME)
    log.info("Loading voice embeddings: %s", voice_path)
    _prefilled_outputs = torch.load(voice_path, map_location=_device, weights_only=False)


def _generate_paragraph_audio(paragraph):
    """Run VibeVoice inference for one paragraph, return audio tensor."""
    import torch

    clean = paragraph.strip()
    clean = clean.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')

    inputs = _processor.process_input_with_cached_prompt(
        text=clean,
        cached_prompt=_prefilled_outputs,
        padding=True,
        return_tensors="pt",
        return_attention_mask=True,
    )
    for k, v in inputs.items():
        if torch.is_tensor(v):
            inputs[k] = v.to(_device)

    outputs = _model.generate(
        **inputs,
        max_new_tokens=None,
        cfg_scale=1.5,
        tokenizer=_processor.tokenizer,
        generation_config={"do_sample": False},
        verbose=False,
        all_prefilled_outputs=copy.deepcopy(_prefilled_outputs),
    )
    return outputs.speech_outputs[0]


def _verify_audio(text, wav_path):
    """Transcribe wav_path with Whisper and return (fuzz_ratio, transcript)."""
    global _whisper_model
    import whisper
    from thefuzz import fuzz

    if _whisper_model is None:
        log.info("Loading Whisper tiny model for audio verification")
        _whisper_model = whisper.load_model("tiny")

    result = _whisper_model.transcribe(wav_path)
    normalized = re.sub(r" +", " ", text).lower().strip()
    ratio = fuzz.ratio(normalized, result["text"].lower().strip())
    return ratio, result["text"]


def synthesize(paragraphs, output_path):
    """Synthesize paragraphs to MP3 using VibeVoice Davis voice.

    Each paragraph is synthesized, verified with Whisper (ratio >= MIN_RATIO),
    and retried up to MAX_RETRIES times on failure.
    """
    _load_model()

    silence = AudioSegment.silent(duration=PARAGRAPH_SILENCE_MS)
    final_audio = AudioSegment.empty()

    with tempfile.TemporaryDirectory(dir="data/tmp") as tmp_dir:
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue

            log.info("VibeVoice paragraph %d/%d", i + 1, len(paragraphs))
            wav_path = os.path.join(tmp_dir, f"para_{i}.wav")

            for attempt in range(1, MAX_RETRIES + 1):
                audio_tensor = _generate_paragraph_audio(paragraph)
                _processor.save_audio(audio_tensor, output_path=wav_path)

                ratio, transcript = _verify_audio(paragraph, wav_path)
                log.info("  Whisper ratio: %d (min=%d)", ratio, MIN_RATIO)

                if ratio >= MIN_RATIO:
                    break

                log.warning(
                    "  Quality check failed (attempt %d/%d)\n  expected: %r\n  got:      %r",
                    attempt, MAX_RETRIES, paragraph[:80], transcript[:80],
                )
                if attempt < MAX_RETRIES:
                    os.remove(wav_path)
                else:
                    log.warning("  Keeping best attempt after %d retries", MAX_RETRIES)

            para_audio = AudioSegment.from_file(wav_path, format="wav")
            if len(final_audio) > 0:
                final_audio += silence
            final_audio += para_audio

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_audio.export(output_path, format="mp3")

    file_size = os.path.getsize(output_path)
    log.info("VibeVoice wrote %s (%d bytes)", output_path, file_size)
    return file_size
