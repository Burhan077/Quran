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
    FONT_PATH = "Arial"  # fallback if font missing

# -------------------------------
# Load Quran Data
# -------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

arabic_quran = load_json(os.path.join(DATA_DIR, "quran_ar.json"))
english_quran = load_json(os.path.join(DATA_DIR, "Quran.json"))

# Reciters and backgrounds
AVAILABLE_RECITERS = [d for d in os.listdir(RECITATIONS_DIR) if os.path.isdir(os.path.join(RECITATIONS_DIR, d))]
AVAILABLE_BACKGROUNDS = [f for f in os.listdir(BACKGROUNDS_DIR) if f.endswith(".mp4")]

# -------------------------------
# STREAMLIT UI
# -------------------------------
st.title(" Quran Recitation Video Generator")

surah_num = st.number_input("Enter Surah Number (1-114)", min_value=1, max_value=114, step=1)
reciter = st.selectbox("Choose Reciter", AVAILABLE_RECITERS)
background = st.selectbox("Choose Background Video", AVAILABLE_BACKGROUNDS)

if st.button("Generate Video "):
    try:
        # Extract verses
        arabic_verses = [v["text"] for v in arabic_quran[str(surah_num)]]

        # Audio file
        audio_path = os.path.join(RECITATIONS_DIR, reciter, f"{surah_num:03d}.mp3")
        if not os.path.isfile(audio_path):
            st.error(f" Recitation file {audio_path} not found.")
            st.stop()

        # Background video
        background_path = os.path.join(BACKGROUNDS_DIR, background)
        if not os.path.isfile(background_path):
            st.error(f" Background video {background_path} not found.")
            st.stop()

        audio_clip = AudioFileClip(audio_path)
        background_clip = VideoFileClip(background_path)

        # Loop background for full audio duration
        final_background = background_clip.loop(duration=audio_clip.duration)

        # Subtitles (Arabic only)
        text_clips = []
        verse_duration = audio_clip.duration / len(arabic_verses)
        for i, arabic in enumerate(arabic_verses):
            txt_clip = TextClip(
                arabic,
                fontsize=50,
                color="white",
                font=FONT_PATH,
                method="caption",
                size=(background_clip.size[0]-100, 200),
                bg_color="black"
            ).set_position("center").set_duration(verse_duration).set_start(i * verse_duration)
            text_clips.append(txt_clip)

        # Combine background + text + audio
        final_clip = CompositeVideoClip([final_background] + text_clips)
        final_clip = final_clip.set_audio(audio_clip)

        # Save output
        output_path = os.path.join(BASE_DIR, f"surah_{surah_num}_{reciter}.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # Preview video
        st.success(" Video generated successfully!")
        st.video(output_path)

        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                label="Download Video",
                data=f,
                file_name=f"surah_{surah_num}_{reciter}.mp4",
                mime="video/mp4"
            )

    except Exception as e:
        st.error(f" Error: {e}")
