import os
import json
import subprocess
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.tools.credits import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from flask import Flask, request, render_template_string, send_file, abort

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECITATIONS_DIR = os.path.join(DATA_DIR, "recitations")
TRANSLATIONS_DIR = os.path.join(DATA_DIR, "translations")
ARABIC_DIR = os.path.join(DATA_DIR, "arabic")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")

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

        arabic_path = os.path.join(ARABIC_DIR, f"surah_{surah_num_int}.json")
        if not os.path.isfile(arabic_path):
            return f"Arabic Surah file {arabic_path} not found", 404

        with open(arabic_path, "r", encoding="utf-8") as f:
            arabic_data = json.load(f)

        translation_path = os.path.join(TRANSLATIONS_DIR, f"en_translation_{surah_num_int}.json")
        if not os.path.isfile(translation_path):
            return f"Translation file {translation_path} not found", 404

        with open(translation_path, "r", encoding="utf-8") as f:
            translation_data = json.load(f)

        verses = []
        for i in range(1, arabic_data.get("count", 0) + 1):
            key = f"verse_{i}"
            arabic_text = arabic_data["verse"].get(key, "")
            translation_text = translation_data["verse"].get(key, "")
            verses.append({"arabic": arabic_text, "translation": translation_text})

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

        # Loop the background video if it's shorter than the audio
        bg_duration = background_clip.duration
        audio_duration = audio_clip.duration

        if bg_duration < audio_duration:
            loops_needed = int(audio_duration // bg_duration) + 1  # Calculate how many loops are needed
            background_clip = background_clip.loop(loops_needed)  # Loop the video
        
        # Trim the background video to match the audio duration
        background_clip = background_clip.subclip(0, audio_clip.duration)

        # Create the final video with text overlays
        text_clips = []
        for i, verse in enumerate(verses):
            # Create text for each verse (Arabic + Translation)
            arabic_text = verse['arabic']
            translation_text = verse['translation']
            text_clip = TextClip(f"{arabic_text}\n{translation_text}", fontsize=40, color='white', bg_color='black', size=background_clip.size, print_cmd=True)
            text_clip = text_clip.set_position('center').set_duration(audio_clip.duration / len(verses)).set_start(i * (audio_clip.duration / len(verses)))
            text_clips.append(text_clip)

        # Combine the background, audio, and text overlays
        final_clip = CompositeVideoClip([background_clip] + text_clips)
        final_clip = final_clip.set_audio(audio_clip)

        # Save the final video to a file
        output_video_path = os.path.join(BASE_DIR, "final_video.mp4")
        final_clip.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

        return send_file(output_video_path, as_attachment=True)

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

    return render_template_string(form_html,
                                  reciters=ALLOWED_RECITERS,
                                  backgrounds=ALLOWED_BACKGROUNDS)


if __name__ == "__main__":
    app.run(debug=True)
