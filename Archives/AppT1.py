import os
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.editor import concatenate_videoclips
from moviepy.config import change_settings
from flask import Flask, request, render_template_string, send_file

# ✅ Fix for Windows ImageMagick path
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q8\magick.exe"})

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECITATIONS_DIR = os.path.join(DATA_DIR, "recitations")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")
FONT_PATH = os.path.join(DATA_DIR, "font", "Amiri-Regular.ttf")

# Load the big JSON files once at startup
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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        surah_num = request.form.get("surah")
        reciter = request.form.get("reciter")
        background = request.form.get("background")

        try:
            surah_num_int = int(surah_num)
            assert 1 <= surah_num_int <= 114
        except:
            return "Invalid Surah number, must be 1-114", 400

        if reciter not in ALLOWED_RECITERS:
            return "Invalid reciter", 400

        if background not in ALLOWED_BACKGROUNDS:
            return "Invalid background", 400

        # Get verses from big JSONs
        arabic_verses = ARABIC_QURAN.get(str(surah_num_int), [])
        english_verses = ENGLISH_QURAN.get(str(surah_num_int), [])

        if not arabic_verses or not english_verses:
            return f"Surah {surah_num_int} not found in JSON files", 404

        # Combine verses into one list
        verses = []
        for a, e in zip(arabic_verses, english_verses):
            verses.append({"arabic": a["text"], "translation": e["text"]})

        # Prepare audio file
        recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
        audio_file = None
        for f_name in os.listdir(recitation_folder):
            if f_name.startswith(f"{surah_num_int:03d}") and f_name.endswith(".mp3"):
                audio_file = f_name
                break

        if not audio_file:
            return f"Recitation audio for Surah {surah_num_int} not found", 404

        audio_path = os.path.join(recitation_folder, audio_file)

        # Prepare the background video
        background_path = os.path.join(BACKGROUNDS_DIR, background)
        if not os.path.isfile(background_path):
            return f"Background video {background} not found", 404

        background_clip = VideoFileClip(background_path)
        audio_clip = AudioFileClip(audio_path)

        # ✅ Loop background video to match audio length
        num_loops = int(audio_clip.duration // background_clip.duration) + 1
        clips = [background_clip] * num_loops
        final_background_clip = concatenate_videoclips(clips)

        # Trim background
        final_background_clip = final_background_clip.subclip(0, audio_clip.duration)

        # Create verse text overlays
        text_clips = []
        verse_duration = audio_clip.duration / len(verses)

        for i, verse in enumerate(verses):
            text_clip = TextClip(
                f"{verse['arabic']}\n{verse['translation']}",
                fontsize=40,
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

        # Combine everything
        final_clip = CompositeVideoClip([final_background_clip] + text_clips)
        final_clip = final_clip.set_audio(audio_clip)

        # Save output
        output_video_path = os.path.join(BASE_DIR, "final_video.mp4")
        final_clip.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

        return send_file(output_video_path, as_attachment=True)

    # Render form
    form_html = """
    <html>
    <head>
      <title>Quran Video Generator</title>
    </head>
    <body>
      <h2>Select Surah, Reciter & Background</h2>
      <form method="POST">
        Surah number (1-114): <input type="number" name="surah" min="1" max="114" required><br><br>

        Reciter:
        <select name="reciter" required>
          {% for reciter in reciters %}
          <option value="{{ reciter }}">{{ reciter.replace('_', ' ') }}</option>
          {% endfor %}
        </select><br><br>

        Background:
        <select name="background" required>
          {% for bg in backgrounds %}
          <option value="{{ bg }}">{{ bg }}</option>
          {% endfor %}
        </select><br><br>

        <input type="submit" value="Generate Video">
      </form>
    </body>
    </html>
    """
    return render_template_string(form_html, reciters=ALLOWED_RECITERS, backgrounds=ALLOWED_BACKGROUNDS)


if __name__ == "__main__":
    app.run(debug=True)
