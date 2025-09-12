import os
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from flask import Flask, request, render_template_string, send_file

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
RECITATIONS_DIR = os.path.join(BASE_DIR, "Recitations")
BACKGROUNDS_DIR = os.path.join(BASE_DIR, "Backgrounds")  # if you keep backgrounds here

# JSON data files
QURAN_EN_PATH = os.path.join(DATA_DIR, "Quran.json")
QURAN_AR_PATH = os.path.join(DATA_DIR, "quran_ar.json")
CHAPTERS_PATH = os.path.join(DATA_DIR, "chapters.json")

ALLOWED_RECITERS = [
    "Mishary_Rashid_Alafasy",
    "Yasir_AlDosari",
    "Idris Akbar"   # matches your folder name
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

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

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

        # Load Arabic & English Quran data
        quran_en = load_json(QURAN_EN_PATH)
        quran_ar = load_json(QURAN_AR_PATH)
        chapters = load_json(CHAPTERS_PATH)

        surah_en = quran_en[str(surah_num_int)]
        surah_ar = quran_ar[str(surah_num_int)]

        # Build verse pairs
        verses = []
        for idx, verse_en in enumerate(surah_en):
            try:
                arabic_text = surah_ar[idx]["text"]
            except IndexError:
                arabic_text = ""
            translation_text = verse_en["text"]
            verses.append({"arabic": arabic_text, "translation": translation_text})

        # Prepare audio file
        recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
        audio_file = f"{surah_num_int:03d}.mp3"
        audio_path = os.path.join(recitation_folder, audio_file)

        if not os.path.isfile(audio_path):
            return f"Recitation audio for Surah {surah_num_int} not found", 404

        # Prepare the background video
        background_path = os.path.join(BACKGROUNDS_DIR, background)
        if not os.path.isfile(background_path):
            return f"Background video {background} not found", 404

        background_clip = VideoFileClip(background_path)
        audio_clip = AudioFileClip(audio_path)

        # Loop background to match audio duration
        num_loops = int(audio_clip.duration // background_clip.duration) + 1
        clips = [background_clip] * num_loops
        final_background_clip = clips[0]
        for clip in clips[1:]:
            final_background_clip = final_background_clip.concatenate_videoclips([clip])
        final_background_clip = final_background_clip.subclipped(0, audio_clip.duration)

        # Create the final video with text overlays
        text_clips = []
        verse_duration = audio_clip.duration / len(verses)

        for i, verse in enumerate(verses):
            combined_text = f"{verse['arabic']}\n{verse['translation']}"
            text_clip = TextClip(
                combined_text,
                fontsize=40,
                color='white',
                font=r"C:\Users\HP\Ideas\Al-Baghdadi1.2\backend\data\font\Amiri-Regular.ttf",
                method='caption',
                size=(background_clip.size[0], 200),
                bg_color='black'
            )
            text_clip = text_clip.set_position('center').set_duration(verse_duration).set_start(i * verse_duration)
            text_clips.append(text_clip)

        # Combine everything
        final_clip = CompositeVideoClip([final_background_clip] + text_clips)
        final_clip = final_clip.set_audio(audio_clip)

        # Save the final video
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
          <option value="{{ reciter }}">{{ reciter }}</option>
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
