import os
import json
import streamlit as st
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
    FONT_PATH = "Arial"  # fallback

# -------------------------------
# Load Data
# -------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

arabic_quran = load_json(os.path.join(DATA_DIR, "quran_ar.json"))
chapters_data = load_json(os.path.join(DATA_DIR, "chapters.json"))

# Map Surah names to IDs
name_to_id = {chap["name"].lower(): chap["id"] for chap in chapters_data}

# Reciters and backgrounds
AVAILABLE_RECITERS = [d for d in os.listdir(RECITATIONS_DIR) if os.path.isdir(os.path.join(RECITATIONS_DIR, d))]
AVAILABLE_BACKGROUNDS = [f for f in os.listdir(BACKGROUNDS_DIR) if f.endswith(".mp4")]

# -------------------------------
# STREAMLIT UI
# -------------------------------
st.title(" Quran Recitation Video Generator")

# Sidebar
with st.sidebar:
    st.header("Select Surah & Options")
    surah_input = st.text_input("Surah number or name (e.g., 4 or Al-Ma'idah)")
    reciter = st.selectbox("Reciter", AVAILABLE_RECITERS)
    background = st.selectbox("Background", AVAILABLE_BACKGROUNDS)

# Preview background
bg_path = os.path.join(BACKGROUNDS_DIR, background)
if os.path.isfile(bg_path):
    st.video(bg_path)

# -------------------------------
# Handle Surah input
# -------------------------------
surah_num = None
if surah_input:
    try:
        if surah_input.isdigit():
            surah_num = int(surah_input)
        else:
            surah_num = name_to_id[surah_input.lower()]
    except:
        st.error(" Invalid Surah name or number")
        st.stop()

# -------------------------------
# Generate Video
# -------------------------------
if st.button("Generate Video ") and surah_num:

    try:
        arabic_verses = [v["text"] for v in arabic_quran[str(surah_num)]]

        # Audio
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
