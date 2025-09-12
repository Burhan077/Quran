import os
import json
import tempfile
import streamlit as st
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip,
    CompositeVideoClip
)
from moviepy.video.fx.loop import loop

# ---------------- PROJECT SETUP ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "Backgrounds")
FONTS_DIR = os.path.join(DATA_DIR, "font")

font_files = [f for f in os.listdir(FONTS_DIR) if f.lower().endswith(".ttf")]
if not font_files:
    raise FileNotFoundError("No TTF font found in Data/fonts/")
FONT_PATH = os.path.join(FONTS_DIR, font_files[0])

# ---------------- LOAD QURAN DATA ----------------
with open(os.path.join(DATA_DIR, "quran_ar.json"), "r", encoding="utf-8") as f:
    ARABIC_QURAN = json.load(f)

with open(os.path.join(DATA_DIR, "quran_en.json"), "r", encoding="utf-8") as f:
    ENGLISH_QURAN = json.load(f)

with open(os.path.join(DATA_DIR, "surahs.txt"), "r", encoding="utf-8") as f:
    SURAH_LIST = [line.strip() for line in f if line.strip()]

# ---------------- RECITERS ----------------
RECITER_URLS = {
    "Sudais": "https://archive.org/download/quran-sudais-193/quran-sudais/",
    "Shuraim": "https://archive.org/download/quran-shuraim-192/quran-shuraim-192/",
    "Alafasy": "https://archive.org/download/quran-alafasy-192/quran-alafasy-192/",
    "Yasir": "https://archive.org/download/quran-yasir-192/quran-yasir-192/",
}

# ---------------- STREAMLIT UI ----------------
st.title("Quran Video Editor")

with st.sidebar:
    st.header("User Controls")
    
    surah_choice = st.selectbox("Choose Surah", SURAH_LIST)
    surah_num = int(surah_choice.split(".")[0].strip())
    
    reciter_choice = st.selectbox("Choose Reciter", list(RECITER_URLS.keys()))
    
    background_files = [f for f in os.listdir(BACKGROUNDS_DIR) if f.lower().endswith(('.mp4','.mov'))]
    background_choice = st.selectbox("Choose Background", background_files)
    
    ayah_range = st.text_input("Ayah Range (e.g 1-3)")

# ---------------- BACKGROUND PREVIEW ----------------
bg_path = os.path.join(BACKGROUNDS_DIR, background_choice)
if os.path.exists(bg_path):
    st.subheader("Background Preview")
    st.video(bg_path)

# ---------------- HELPER FUNCTIONS ----------------
def get_audio_url(reciter, surah, verse):
    return f"{RECITER_URLS[reciter]}{surah:03d}{verse:03d}.mp3"

def download_audio(reciter, surah, start, end, progress_bar=None):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    total = end - start + 1
    for i, verse in enumerate(range(start, end+1)):
        url = get_audio_url(reciter, surah, verse)
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

def prepare_text_images(surah_num, start, end, width, height, font_path):
    arabic_verses = ARABIC_QURAN.get(str(surah_num), [])[start-1:end]
    english_verses = ENGLISH_QURAN.get(str(surah_num), [])[start-1:end]
    images = []
    font = ImageFont.truetype(font_path, 50)
    for a, e in zip(arabic_verses, english_verses):
        reshaped = arabic_reshaper.reshape(a["text"])
        bidi_text = get_display(reshaped)
        img = Image.new("RGBA", (width, height), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.text((10,10), bidi_text, font=font, fill="white")           # Arabic
        draw.text((10, height//2), e["text"], font=font, fill="gray")    # English
        img_array = np.array(img)
        images.append(ImageClip(img_array))
    return images

# ---------------- UI: Buttons ----------------
col1, col2 = st.columns([1,1])
with col1:
    generate_clicked = st.button("Generate Video")
with col2:
    download_button_placeholder = st.empty()

progress_bar = st.progress(0)

# ---------------- VIDEO GENERATION ----------------
if generate_clicked:
    try:
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

        # Download audio
        audio_path = download_audio(reciter_choice, surah_num, start, end, progress_bar)
        audio_clip = AudioFileClip(audio_path)

        # Background video
        bg_clip = VideoFileClip(bg_path)
        final_bg = loop(bg_clip, duration=audio_clip.duration)

        # Prepare text images
        text_clips = prepare_text_images(surah_num, start, end, final_bg.size[0]-100, 250, FONT_PATH)
        verse_duration = audio_clip.duration / len(text_clips)
        for i, clip in enumerate(text_clips):
            clip = clip.set_duration(verse_duration).set_start(i*verse_duration).set_position("center")
            text_clips[i] = clip

        # Combine background + text + audio
        final_clip = CompositeVideoClip([final_bg]+text_clips).set_audio(audio_clip)

        # Choose output path
        user_downloads = os.path.expanduser("~/Downloads")
        if os.path.exists(user_downloads):
            output_path = os.path.join(user_downloads, f"surah_{surah_num}_{start}-{end}_{reciter_choice}.mp4")
        else:
            output_path = os.path.join(BASE_DIR, f"surah_{surah_num}_{start}-{end}_{reciter_choice}.mp4")

        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")

        # Add download button
        with open(output_path, "rb") as f:
            download_button_placeholder.download_button(
                "⬇ Download Video",
                f,
                file_name=os.path.basename(output_path),
                mime="video/mp4",
                disabled=False
            )

        st.success("Video generated successfully!")

        # Cleanup temp audio
        os.unlink(audio_path)

    except Exception as e:
        st.error(f"Error: {e}")
