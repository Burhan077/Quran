import os
import json
import streamlit as st
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.editor import concatenate_videoclips
from moviepy.config import change_settings

# ✅ Fix for Windows ImageMagick path
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q8\magick.exe"})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECITATIONS_DIR = os.path.join(DATA_DIR, "recitations")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")
FONT_PATH = os.path.join(DATA_DIR, "font", "Amiri-Regular.ttf")

# Load JSON once
ARABIC_FILE = os.path.join(DATA_DIR, "quran_ar.json")
ENGLISH_FILE = os.path.join(DATA_DIR, "quran_en.json")

with open(ARABIC_FILE, "r", encoding="utf-8") as f:
    ARABIC_QURAN = json.load(f)

with open(ENGLISH_FILE, "r", encoding="utf-8") as f:
    ENGLISH_QURAN = json.load(f)

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

surah_num = st.number_input("Surah number (1-114):", min_value=1, max_value=114, step=1)

reciter = st.selectbox("Choose Reciter:", ALLOWED_RECITERS)

background = st.selectbox("Choose Background:", ALLOWED_BACKGROUNDS)

if st.button("Generate Video"):
    try:
        surah_num_int = int(surah_num)
        arabic_verses = ARABIC_QURAN.get(str(surah_num_int), [])
        english_verses = ENGLISH_QURAN.get(str(surah_num_int), [])

        if not arabic_verses or not english_verses:
            st.error(f"❌ Surah {surah_num_int} not found in JSON files")
        else:
            verses = []
            for a, e in zip(arabic_verses, english_verses):
                verses.append({"arabic": a["text"], "translation": e["text"]})

            # Recitation
            recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
            audio_file = None
            for f_name in os.listdir(recitation_folder):
                if f_name.startswith(f"{surah_num_int:03d}") and f_name.endswith(".mp3"):
                    audio_file = f_name
                    break

            if not audio_file:
                st.error(f"❌ Recitation audio for Surah {surah_num_int} not found")
            else:
                audio_path = os.path.join(recitation_folder, audio_file)
                background_path = os.path.join(BACKGROUNDS_DIR, background)

                background_clip = VideoFileClip(background_path)
                audio_clip = AudioFileClip(audio_path)

                # Loop background
                num_loops = int(audio_clip.duration // background_clip.duration) + 1
                clips = [background_clip] * num_loops
                final_background_clip = concatenate_videoclips(clips)
                final_background_clip = final_background_clip.subclip(0, audio_clip.duration)

                # Verse overlays
                text_clips = []
                verse_duration = audio_clip.duration / len(verses)

                for i, verse in enumerate(verses):
                    text_clip = TextClip(
                        f"{verse['arabic']}\n{verse['translation']}",
                        fontsize=50,
                        color="white",
                        font=FONT_PATH,
                        method="caption",
                        size=(background_clip.size[0], 100),
                        bg_color="black"
                    )
                    text_clip = (
                        text_clip.set_position("center")
                        .set_duration(verse_duration)
                        .set_start(i * verse_duration)
                    )
                    text_clips.append(text_clip)

                # Combine
                final_clip = CompositeVideoClip([final_background_clip] + text_clips)
                final_clip = final_clip.set_audio(audio_clip)

                # Save
                output_video_path = os.path.join(BASE_DIR, "final_video.mp4")
                final_clip.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

                st.success("✅ Video generated successfully!")
                st.video(output_video_path)
                with open(output_video_path, "rb") as f:
                    st.download_button("📥 Download Video", f, file_name="final_video.mp4")

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
