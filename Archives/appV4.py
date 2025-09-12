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
    FONT_PATH = "Arial"  # fallback

# -------------------------------
# LOAD DATA
# -------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

arabic_quran = load_json(os.path.join(DATA_DIR, "quran_ar.json"))
chapters_data = load_json(os.path.join(DATA_DIR, "chapters.json"))

# Load Surah names from surahs.txt
SURAH_TXT_PATH = os.path.join(DATA_DIR, "surahs.txt")
surah_names = []
with open(SURAH_TXT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            name = line.split('.', 1)[1].strip() if '.' in line else line
            surah_names.append(name)

surah_options = [(f"{i+1:03d} - {name}", i+1) for i, name in enumerate(surah_names)]

# Available reciters and backgrounds
AVAILABLE_RECITERS = [d for d in os.listdir(RECITATIONS_DIR) if os.path.isdir(os.path.join(RECITATIONS_DIR, d))]
AVAILABLE_BACKGROUNDS = [f for f in os.listdir(BACKGROUNDS_DIR) if f.endswith(".mp4")]

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def parse_verse_range(input_text, total_verses):
    """Returns start and end verse numbers"""
    if not input_text.strip():
        return 1, total_verses
    try:
        parts = input_text.split('-')
        start = int(parts[0])
        end = int(parts[1]) if len(parts) > 1 else start
        start = max(1, min(start, total_verses))
        end = max(1, min(end, total_verses))
        if start > end:
            start, end = end, start
        return start, end
    except:
        return 1, total_verses

# -------------------------------
# STREAMLIT UI
# -------------------------------
st.title("Quran Video Generator")

with st.sidebar:
    st.header("Select Options")

    # Surah dropdown
    surah_num = st.selectbox(
        "Select Surah",
        options=surah_options,
        format_func=lambda x: x[0]
    )[1]

    selected_chap = next(c for c in chapters_data if c["id"] == surah_num)
    st.write(f"**Type:** {selected_chap['type'].title()}")
    st.write(f"**Total Verses:** {selected_chap['total_verses']}")

    # Verse range input
    verse_range_input = st.text_input(
        "Select Ayahs (e.g., 1-5). Leave empty for full Surah",
        value=""
    )

    # Reciter and background
    reciter = st.selectbox("Select Reciter", AVAILABLE_RECITERS)
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
        # Determine verse numbers
        total_verses = selected_chap['total_verses']
        start_verse, end_verse = parse_verse_range(verse_range_input, total_verses)
        verse_numbers = list(range(start_verse, end_verse + 1))

        # Extract Arabic verses
        arabic_verses = [arabic_quran[str(surah_num)][v-1]["text"] for v in verse_numbers]

        # Audio path
        audio_path = os.path.join(RECITATIONS_DIR, reciter, f"{surah_num:03d}.mp3")
        if not os.path.isfile(audio_path):
            st.error(f" Recitation file {audio_path} not found.")
            st.stop()

        # Load audio & clip to selected verse range
        audio_clip = AudioFileClip(audio_path)
        verse_duration = audio_clip.duration / total_verses
        start_time = (start_verse - 1) * verse_duration
        end_time = end_verse * verse_duration
        audio_clip = audio_clip.subclipped(start_time, end_time)

        # Load background
        bg_clip = VideoFileClip(bg_path)

        # Loop background manually (concatenate)
        num_loops = int(audio_clip.duration // bg_clip.duration) + 1
        bg_clips = [bg_clip] * num_loops
        final_background = bg_clips[0]
        for clip in bg_clips[1:]:
            final_background = final_background.concatenate_videoclips([clip])
        final_background = final_background.subclipped(0, audio_clip.duration)

        # Create subtitles
        verse_duration_clip = audio_clip.duration / len(arabic_verses)
        text_clips = []
        for i, arabic in enumerate(arabic_verses):
            txt_clip = TextClip(
                arabic,
                fontsize=50,
                color="white",
                font=FONT_PATH,
                method="caption",
                size=(bg_clip.size[0]-100, 200),
                bg_color="black"
            ).set_position("center").set_duration(verse_duration_clip).set_start(i * verse_duration_clip)
            text_clips.append(txt_clip)

        # Combine video + subtitles + audio
        final_clip = CompositeVideoClip([final_background] + text_clips)
        final_clip = final_clip.set_audio(audio_clip)

        # Save output
        output_filename = f"surah_{surah_num}_{start_verse}-{end_verse}_{reciter}.mp4"
        output_path = os.path.join(BASE_DIR, output_filename)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # Show preview + download
        st.success("Video generated successfully!")
        col1, col2 = st.columns(2)
        with col1:
            st.video(output_path)
        with col2:
            with open(output_path, "rb") as f:
                st.download_button(" Download Video", f, file_name=output_filename)

    except Exception as e:
        st.error(f" Error: {e}")
