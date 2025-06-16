import argparse
import os
import numpy as np
import re
import soundfile
import subprocess
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import warnings
import sys
from tqdm import tqdm
import nltk
from nltk.tokenize import sent_tokenize

import soundfile as sf
from lxml import etree
from mutagen import mp4
from pydub import AudioSegment


warnings.filterwarnings("ignore")

def ensure_punkt():
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab")

def sort_key(s):
    # extract number from the string
    return int(re.findall(r'\d+', s)[0])

def append_silence(tempfile, duration=1200):
    audio = AudioSegment.from_file(tempfile)
    # Create a silence segment
    silence = AudioSegment.silent(duration)
    # Append the silence segment to the audio
    combined = audio + silence
    # Save the combined audio back to file
    out_f = combined.export(tempfile, format="wav")
    out_f.close()

def chatterbox_read(sentences, sample, filenames, model):
    for i, sent in enumerate(sentences):
        wav = model.generate(sent, audio_prompt_path="voices/"+sample)
        ta.save(filenames[i], wav, model.sr)

def read_article(paragraphs, speaker, filename):
    # Requires cuda
    model = ChatterboxTTS.from_pretrained(device="cuda")
    files = []
    for i, text in enumerate(paragraphs):
        sentences = sent_tokenize(text)
        filenames = [
            "sntnc" + str(z) + ".wav" for z in range(len(sentences))
        ]
        chatterbox_read(sentences, speaker, filenames, model)
        append_silence(filenames[-1], 600)
        combined = AudioSegment.empty()
        for file in filenames:
            combined += AudioSegment.from_file(file)
        combined.export(f"pgraph{i}.wav", format="wav")
        for file in filenames:
            os.remove(file)
        files.append(f"pgraph{i}.wav")
    combined = AudioSegment.empty()
    for file in files:
        combined += AudioSegment.from_file(file)
    combined.export(filename, format="mp3")
    for file in files:
        os.remove(file)

ensure_punkt()
