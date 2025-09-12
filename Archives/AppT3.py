import os
import streamlit as st
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# -------------------------------
# PATHS
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
RECITATIONS_DIR = os.path.join(BASE_DIR, "Recitations")
BACKGROUNDS_DIR = os.path.join(BASE_DIR, "Backgrounds")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")

FONT_PATH = os.path.join(FONTS_DIR, "Amiri-Regular.ttf")
if not os.path.isfile(FONT_PATH):
    FONT_PATH = "Arial"  # fallback font

# -------------------------------
# LOAD DATA
# -------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

arabic_quran = load_json(os.path.join(DATA_DIR, "quran_ar.json"))
chapters_data = load_json(os.path.join(DATA_DIR, "chapters.json"))

# Load Surah names from surahs.txt and remove numbering
SURAH_TXT_PATH = os.path.join(DATA_DIR, "surahs.txt")
surah_names = []
with open(SURAH_TXT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            # Remove leading numbers like "1. Al-Fatihah" -> "Al-Fatihah"
            name = line.split('.', 1)[1].strip() if '.' in line else line
            surah_names.append(name)

# Build dropdown options: ("001 - Al-Fatihah", 1)
surah_options = [(f"{i+1:03d} - {name}", i+1) for i, name in enumerate(surah_names)]

# Available reciters and backgrounds
AVAILABLE_RECITERS = [d for d in os.listdir(RECITATIONS_DIR) if os.path.isdir(os.path.join(RECITATIONS_DIR, d))]
AVAILABLE_BACKGROUNDS = [f for f in os.listdir(BACKGROUNDS_DIR) if f.endswith(".mp4")]

# -------------------------------
# STREAMLIT UI
# -------------------------------
st.title(" Quran Video Generator")

with st.sidebar:
    st.header("Select Options")

    # Surah dropdown
    surah_num = st.selectbox(
        "Select Surah",
        options=surah_options,
        format_func=lambda x: x[0]
    )[1]  # actual Surah number

    # Surah info from chapters.json
    selected_chap = next(c for c in chapters_data if c["id"] == surah_num)
    st.write(f"**Type:** {selected_chap['type'].title()}")
    st.write(f"**Total Verses:** {selected_chap['total_verses']}")

    # Reciter
    reciter = st.selectbox("Select Reciter", AVAILABLE_RECITERS)

    # Background
    background = st.selectbox("Select Background", AVAILABLE_BACKGROUNDS)

# -------------------------------
# Preview background
# -------------------------------
bg_path = os.path.join(BACKGROUNDS_DIR, background)
if os.path.isfile(bg_path):
    st.video(bg_path)

# -------------------------------
# Generate Video
# -------------------------------
if st.button("Generate Video"):

    try:
        arabic_verses = [v["text"] for v in arabic_quran[str(surah_num)]]

        # Audio path
        audio_path = os.path.join(RECITATIONS_DIR, reciter, f"{surah_num:03d}.mp3")
        if not os.path.isfile(audio_path):
            st.error(f" Recitation file {audio_path} not found.")
            st.stop()

        audio_clip = AudioFileClip(audio_path)
        bg_clip = VideoFileClip(bg_path)

        # -------------------------------
        # Loop background manually
        # -------------------------------
        num_loops = int(audio_clip.duration // bg_clip.duration) + 1
        looped_clips = []
        for i in range(num_loops):
            looped_clips.append(bg_clip.set_start(i * bg_clip.duration))
        final_background = CompositeVideoClip(looped_clips).subclipped(0, audio_clip.duration)

        # -------------------------------
        # Subtitles (Arabic only)
        # -------------------------------
        text_clips = []
        verse_duration = audio_clip.duration / len(arabic_verses)
        for i, arabic in enumerate(arabic_verses):
            txt_clip = TextClip(
                arabic,
                fontsize=50,
                color="white",
                font=FONT_PATH,
                method="caption",
                size=(bg_clip.size[0]-100, 200),
                bg_color="black"
            ).set_position("center").set_duration(verse_duration).set_start(i * verse_duration)
            text_clips.append(txt_clip)

        # -------------------------------
        # Combine video + text + audio
        # -------------------------------
        final_clip = CompositeVideoClip([final_background] + text_clips)
        final_clip = final_clip.set_audio(audio_clip)

        # Save output
        output_filename = f"surah_{surah_num}_{reciter}.mp4"
        output_path = os.path.join(BASE_DIR, output_filename)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # -------------------------------
        # Preview + download side by side
        # -------------------------------
        st.success(" Video generated successfully!")
        col1, col2 = st.columns(2)
        with col1:
            st.video(output_path)
        with col2:
            with open(output_path, "rb") as f:
                st.download_button(" Download Video", f, file_name=output_filename)

    except Exception as e:
        st.error(f" Error: {e}")
