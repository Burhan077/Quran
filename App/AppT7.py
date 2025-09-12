import os
import json
import streamlit as st
import arabic_reshaper
from bidi.algorithm import get_display
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from moviepy.config import change_settings
import requests
import tempfile

# ---------------- SETTINGS ----------------
# Fix ImageMagick path (Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q8\magick.exe"})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")
FONT_PATH = os.path.join(DATA_DIR, "font", "Amiri-Regular.ttf")

# ---------------- LOAD QURAN DATA ----------------
with open(os.path.join(DATA_DIR, "quran_ar.json"), "r", encoding="utf-8") as f:
    ARABIC_QURAN = json.load(f)

with open(os.path.join(DATA_DIR, "quran_en.json"), "r", encoding="utf-8") as f:
    ENGLISH_QURAN = json.load(f)

# Load Surah list
SURAH_LIST = []
with open(os.path.join(DATA_DIR, "surahs.txt"), "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            SURAH_LIST.append(line)

# ---------------- OPTIONS ----------------
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
st.title("📖 Quran Video Generator (Streaming Audio)")

with st.sidebar:
    st.header("⚙️ User Controls")

    # Surah dropdown
    surah_choice = st.selectbox("📖 Choose Surah", SURAH_LIST)
    surah_num = int(surah_choice.split(".")[0].strip())

    # Background dropdown
    background = st.selectbox("🌌 Choose Background", ALLOWED_BACKGROUNDS)

    # Ayah range
    ayah_range = st.text_input("🔢 Ayah Range (e.g. 1-3). Leave blank for full Surah")

# Preview background
bg_path = os.path.join(BACKGROUNDS_DIR, background)
if os.path.exists(bg_path):
    st.video(bg_path)

# ---------------- HELPER FUNCTIONS ----------------
def get_audio_url(surah, verse):
    """Return archive.org URL for Sudais recitation MP3"""
    return f"https://archive.org/download/quran-sudais-192/quran-sudais-192/{surah:03d}{verse:03d}.mp3"

def download_audio(surah, start_verse, end_verse, progress_bar=None):
    """Download multiple verse MP3s from archive.org into one temp file"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    total = end_verse - start_verse + 1
    for i, verse in enumerate(range(start_verse, end_verse+1)):
        url = get_audio_url(surah, verse)
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            for chunk in r.iter_content(chunk_size=1024*1024):
                temp_file.write(chunk)
        else:
            raise Exception(f"Failed to download {url}")
        if progress_bar:
            progress_bar.progress((i+1)/total)
    temp_file.flush()
    return temp_file.name

def prepare_texts(surah_num, start, end):
    """Return list of dicts: {'arabic': ..., 'translation': ...}"""
    arabic_verses = ARABIC_QURAN.get(str(surah_num), [])
    english_verses = ENGLISH_QURAN.get(str(surah_num), [])
    selected_arabic = arabic_verses[start-1:end]
    selected_english = english_verses[start-1:end]

    verses = []
    for a, e in zip(selected_arabic, selected_english):
        reshaped = arabic_reshaper.reshape(a["text"])
        bidi_text = get_display(reshaped)
        verses.append({"arabic": bidi_text, "translation": e["text"]})
    return verses

# ---------------- GENERATE VIDEO ----------------
if st.button("🚀 Generate Video"):
    try:
        # Parse ayah range
        total_verses = len(ARABIC_QURAN.get(str(surah_num), []))
        if ayah_range.strip():
            parts = ayah_range.split("-")
            start = int(parts[0])
            end = int(parts[1]) if len(parts) > 1 else start
            start = max(1, min(start, total_verses))
            end = max(1, min(end, total_verses))
            if start > end:
                start, end = end, start
        else:
            start, end = 1, total_verses

        # Prepare text
        verses = prepare_texts(surah_num, start, end)

        # Download audio
        progress_bar = st.progress(0)
        audio_path = download_audio(surah_num, start, end, progress_bar)
        audio_clip = AudioFileClip(audio_path)

        # Load background and loop
        bg_clip = VideoFileClip(bg_path)
        loops = int(audio_clip.duration // bg_clip.duration) + 1
        final_bg = concatenate_videoclips([bg_clip]*loops).subclip(0, audio_clip.duration)

        # Text overlays
        text_clips = []
        verse_clip_duration = audio_clip.duration / len(verses)
        for i, verse in enumerate(verses):
            txt = f"{verse['arabic']}\n{verse['translation']}"
            txt_clip = TextClip(
                txt,
                fontsize=50,
                color="white",
                font=FONT_PATH,
                method="caption",
                size=(bg_clip.size[0], 100),
                bg_color="black"
            ).set_position("center").set_duration(verse_clip_duration).set_start(i*verse_clip_duration)
            text_clips.append(txt_clip)

        # Combine
        final_clip = CompositeVideoClip([final_bg]+text_clips).set_audio(audio_clip)

        # Save
        output_path = os.path.join(BASE_DIR, f"surah_{surah_num}_{start}-{end}_Sudais.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        st.success("Video generated successfully!")
        st.video(output_path)
        with open(output_path, "rb") as f:
            st.download_button(" Download Video", f, file_name=os.path.basename(output_path))

        # Cleanup temp audio
        os.unlink(audio_path)

    except Exception as e:
        st.error(f"Error: {e}")
