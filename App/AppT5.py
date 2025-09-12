import os
import json
import streamlit as st
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.editor import concatenate_videoclips
from moviepy.config import change_settings

import arabic_reshaper
from bidi.algorithm import get_display

# Fix ImageMagick path (Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q8\magick.exe"})

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECITATIONS_DIR = os.path.join(DATA_DIR, "recitations")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")
FONT_PATH = os.path.join(DATA_DIR, "font", "Amiri-Regular.ttf")

# ---------------- LOAD DATA ----------------
with open(os.path.join(DATA_DIR, "quran_ar.json"), "r", encoding="utf-8") as f:
    ARABIC_QURAN = json.load(f)

with open(os.path.join(DATA_DIR, "quran_en.json"), "r", encoding="utf-8") as f:
    ENGLISH_QURAN = json.load(f)

ALLOWED_RECITERS = ["Mishary_Rashid_Alafasy", "Yasir_AlDosari", "Idris_Akbar"]
ALLOWED_BACKGROUNDS = [f for f in os.listdir(BACKGROUNDS_DIR) if f.endswith(".mp4")]

# ---------------- HELPERS ----------------
def fix_arabic(text: str) -> str:
    reshaped_text = arabic_reshaper.reshape(text)   # connect letters
    bidi_text = get_display(reshaped_text)          # right-to-left
    return bidi_text

# ---------------- STREAMLIT LAYOUT ----------------
st.set_page_config(page_title="Quran Video Generator", layout="wide")

# Sidebar controls
with st.sidebar:
    st.header("Options")
    surah_num = st.number_input("Surah number (1-114):", min_value=1, max_value=114, step=1)
    verse_range = st.text_input("Ayah range (e.g. 1-3, leave empty for all):", "")
    reciter = st.selectbox(" Reciter", ALLOWED_RECITERS)
    background = st.selectbox(" Background", ALLOWED_BACKGROUNDS)
    generate = st.button(" Generate Video")

# Main content
st.title("Quran Video Generator")

# Background preview
bg_path = os.path.join(BACKGROUNDS_DIR, background)
if os.path.isfile(bg_path):
    st.video(bg_path)

# Generate
if generate:
    try:
        surah = ARABIC_QURAN.get(str(surah_num), [])
        translation = ENGLISH_QURAN.get(str(surah_num), [])
        if not surah or not translation:
            st.error("Surah not found in data")
            st.stop()

        # Pick verses
        total_verses = len(surah)
        if verse_range.strip():
            try:
                start, end = map(int, verse_range.split("-"))
            except:
                start, end = 1, total_verses
        else:
            start, end = 1, total_verses
        start, end = max(1, start), min(total_verses, end)
        verses = [
            {"arabic": fix_arabic(surah[i]["text"]), "translation": translation[i]["text"]}
            for i in range(start - 1, end)
        ]

        # Load audio
        recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
        audio_file = None
        for f_name in os.listdir(recitation_folder):
            if f_name.startswith(f"{surah_num:03d}") and f_name.endswith(".mp3"):
                audio_file = f_name
                break
        if not audio_file:
            st.error(" Recitation audio not found")
            st.stop()

        audio_clip = AudioFileClip(os.path.join(recitation_folder, audio_file))

        # Approximate clipping by verse count
        verse_duration = audio_clip.duration / total_verses
        start_time = (start - 1) * verse_duration
        end_time = end * verse_duration
        audio_clip = audio_clip.subclip(start_time, end_time)

        # Background looping
        bg_clip = VideoFileClip(bg_path)
        loops = int(audio_clip.duration // bg_clip.duration) + 1
        bg_final = concatenate_videoclips([bg_clip] * loops).subclip(0, audio_clip.duration)

        # Verse overlays
        text_clips = []
        verse_dur = audio_clip.duration / len(verses)
        for i, v in enumerate(verses):
            full_text = f"{v['arabic']}\n{v['translation']}"
            txt = TextClip(
                full_text,
                fontsize=40,
                font=FONT_PATH,
                color="white",
                method="caption",
                size=(bg_clip.size[0], 150),
                bg_color="black"
            )
            txt = txt.set_position("center").set_start(i * verse_dur).set_duration(verse_dur)
            text_clips.append(txt)

        final_clip = CompositeVideoClip([bg_final] + text_clips).set_audio(audio_clip)

        # Output
        out_file = os.path.join(BASE_DIR, f"surah_{surah_num}_{start}-{end}.mp4")

        progress = st.progress(0)
        final_clip.write_videofile(
            out_file,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger=None  # suppress spam
        )
        progress.progress(100)

        st.success("Video generated successfully!")

        # Download + progress bar row
        col1, col2 = st.columns([4, 1])
        with col1:
            st.video(out_file) 
        with col2:
            with open(out_file, "rb") as f:
                st.download_button("📥 Download", f, file_name=os.path.basename(out_file))

    except Exception as e:
        st.error(f"Error: {e}")
