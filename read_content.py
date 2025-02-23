import argparse
import os
import numpy as np
import re
import soundfile
import subprocess
import torch
import warnings
import sys
from tqdm import tqdm
from kokoro import KPipeline

import soundfile as sf
from lxml import etree
from mutagen import mp4
from pydub import AudioSegment


warnings.filterwarnings("ignore", module="kokoro.KPipeline")

def sort_key(s):
    # extract number from the string
    return int(re.findall(r'\d+', s)[0])

def check_for_file(filename):
    if os.path.isfile(filename):
        print(f"The file '{filename}' already exists.")
        overwrite = input("Do you want to overwrite the file? (y/n): ")
        if overwrite.lower() != 'y':
            print("Exiting without overwriting the file.")
            sys.exit()
        else:
            os.remove(filename)

def append_silence(tempfile, duration=1200):
    audio = AudioSegment.from_file(tempfile)
    # Create a silence segment
    silence = AudioSegment.silent(duration)
    # Append the silence segment to the audio
    combined = audio + silence
    # Save the combined audio back to file
    combined.export(tempfile, format="wav")

def kokoro_read(paragraph, speaker, filename, pipeline, speed):
    audio_segments = []
    for gs, ps, audio in pipeline(paragraph, voice=speaker, speed=speed, split_pattern=r'\n\n\n'):
        audio_segments.append(audio)
    final_audio = np.concatenate(audio_segments)
    soundfile.write(filename, final_audio, 24000)

def read_article(paragraphs, speaker, filename, speed):
    if torch.cuda.is_available():
        torch.set_default_device('cuda')
    files = []
    pipeline = KPipeline(lang_code=speaker[0])
    for i, text in enumerate(paragraphs):
        file = f"pgraph{i}.wav"
        #print(f"Reading to {file} with {text}")
        kokoro_read(text, speaker, file, pipeline, speed)
        append_silence(file, 600)
        files.append(file)
    sorted_files = sorted(files, key=sort_key)
    combined = AudioSegment.empty()
    for file in sorted_files:
        combined += AudioSegment.from_file(file)
    combined.export(filename, format="mp3")
    for file in sorted_files:
        os.remove(file)
