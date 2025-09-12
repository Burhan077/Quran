import os
import json
import streamlit as st
import arabic_reshaper
from bidi.algorithm import get_display
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.editor import concatenate_videoclips
from moviepy.config import change_settings

# ---------------- SETTINGS ----------------
# Fix ImageMagick path (Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q8\magick.exe"})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECITATIONS_DIR = os.path.join(DATA_DIR, "recitations")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")
FONT_PATH = os.path.join(DATA_DIR, "font", "Amiri-Regular.ttf")

# ---------------- LOAD QURAN DATA ----------------
with open(os.path.join(DATA_DIR, "quran_ar.json"), "r", encoding="utf-8") as f:
    ARABIC_QURAN = json.load(f)

with open(os.path.join(DATA_DIR, "quran_en.json"), "r", encoding="utf-8") as f:
    ENGLISH_QURAN = json.load(f)

# Load Surah list from file
SURAH_LIST = []
with open(os.path.join(DATA_DIR, "surahs.txt"), "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            SURAH_LIST.append(line)

# ---------------- OPTIONS ----------------
ALLOWED_RECITERS = [
    "Mishary_Rashid_Alafasy",
    "Yasir_AlDosari",
    "Idris_Akbar"
]

ALLOWED_BACKGROUNDS = [
    "nebulae.mp4",
    "mountain.mp4",
    "cliffs.mp4",
    "junct.mp4",
    "sea.mp4",
    "track.mp4",
    "sky.mp4",
    "snow.mp4",
    "solar.mp4"
]

# ---------------- STREAMLIT UI ----------------
st.title("📖 Quran Video Generator")

with st.sidebar:
    st.header("⚙️ User Controls")

    # Surah dropdown
    surah_choice = st.selectbox("📖 Choose Surah", SURAH_LIST)
    surah_num = int(surah_choice.split(".")[0].strip())

    # Reciter dropdown
    reciter = st.selectbox("🎙️ Choose Reciter", ALLOWED_RECITERS)

    # Background dropdown
    background = st.selectbox("🌌 Choose Background", ALLOWED_BACKGROUNDS)

    # Ayah range
    ayah_range = st.text_input("🔢 Ayah Range (e.g. 1-3). Leave blank for full Surah")

# Preview background
bg_path = os.path.join(BACKGROUNDS_DIR, background)
if os.path.exists(bg_path):
    st.video(bg_path)

# ---------------- GENERATE VIDEO ----------------
if st.button("🚀 Generate Video"):
    try:
        # Load verses
        arabic_verses = ARABIC_QURAN.get(str(surah_num), [])
        english_verses = ENGLISH_QURAN.get(str(surah_num), [])
        total_verses = len(arabic_verses)

        if not arabic_verses or not english_verses:
            st.error(f"❌ Surah {surah_num} not found in JSON files")
            st.stop()

        # Parse ayah range
        if ayah_range.strip():
            try:
                parts = ayah_range.split("-")
                start = int(parts[0])
                end = int(parts[1]) if len(parts) > 1 else start
                start = max(1, min(start, total_verses))
                end = max(1, min(end, total_verses))
                if start > end:
                    start, end = end, start
            except:
                start, end = 1, total_verses
        else:
            start, end = 1, total_verses

        selected_arabic = arabic_verses[start-1:end]
        selected_english = english_verses[start-1:end]

        verses = []
        for a, e in zip(selected_arabic, selected_english):
            reshaped = arabic_reshaper.reshape(a["text"])
            bidi_text = get_display(reshaped)
            verses.append({"arabic": bidi_text, "translation": e["text"]})

        # Recitation file
        recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
        audio_file = f"{surah_num:03d}.mp3"   # e.g., "006.mp3"
        audio_path = os.path.join(recitation_folder, audio_file)

        if not os.path.exists(audio_path):
            st.error(f"❌ Audio file {audio_file} not found for {reciter}")
            st.stop()

        audio_clip = AudioFileClip(audio_path)

        # Clip audio to selected verses (approximation)
        verse_duration = audio_clip.duration / total_verses
        start_time = (start-1) * verse_duration
        end_time = end * verse_duration
        audio_clip = audio_clip.subclip(start_time, end_time)

        # Background
        bg_clip = VideoFileClip(bg_path)
        loops = int(audio_clip.duration // bg_clip.duration) + 1
        final_bg = concatenate_videoclips([bg_clip] * loops).subclip(0, audio_clip.duration)

        # Text overlays
        text_clips = []
        verse_clip_duration = audio_clip.duration / len(verses)

        for i, verse in enumerate(verses):
            txt = f"{verse['arabic']}\n{verse['translation']}"
            txt_clip = TextClip(
                txt,
                fontsize=40,
                color="white",
                font=FONT_PATH,
                method="caption",
                size=(bg_clip.size[0]-100, 200),
                bg_color="black"
            ).set_position("center").set_duration(verse_clip_duration).set_start(i*verse_clip_duration)
            text_clips.append(txt_clip)

        # Combine
        final_clip = CompositeVideoClip([final_bg] + text_clips).set_audio(audio_clip)

        # Save
        output_path = os.path.join(BASE_DIR, f"surah_{surah_num}_{start}-{end}_{reciter}.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        st.success("✅ Video generated successfully!")
        st.video(output_path)
        with open(output_path, "rb") as f:
            st.download_button("📥 Download Video", f, file_name=os.path.basename(output_path))

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
