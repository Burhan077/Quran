import os
import json
from flask import Flask, request, render_template_string, send_file, abort

app = Flask(__name__)

# Base directories - relative to this app.py location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECITATIONS_DIR = os.path.join(DATA_DIR, "recitations")
TRANSLATIONS_DIR = os.path.join(DATA_DIR, "translations")
ARABIC_DIR = os.path.join(DATA_DIR, "arabic")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")  # stock loop videos here

# Allowed reciters (you can expand this list)
ALLOWED_RECITERS = [
    "Mishary_Rashid_Alafasy",
    "Yasir_AlDosari",
    "Idris_Akbar"
]

# Allowed backgrounds (sample names of your video loops)
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
        # Get form data
        surah_num = request.form.get("surah")
        reciter = request.form.get("reciter")
        background = request.form.get("background")

        # Validate inputs
        try:
            surah_num_int = int(surah_num)
            assert 1 <= surah_num_int <= 114
        except:
            return "Invalid Surah number, must be 1-114", 400

        if reciter not in ALLOWED_RECITERS:
            return "Invalid reciter", 400

        if background not in ALLOWED_BACKGROUNDS:
            return "Invalid background", 400

        # Load Arabic JSON
        arabic_path = os.path.join(ARABIC_DIR, f"surah_{surah_num_int:03d}.json")
        if not os.path.isfile(arabic_path):
            return f"Arabic Surah file {arabic_path} not found", 404

        with open(arabic_path, "r", encoding="utf-8") as f:
            arabic_data = json.load(f)

        # Load Translation JSON
        translation_path = os.path.join(TRANSLATIONS_DIR, f"en_translation_{surah_num_int}.json")
        if not os.path.isfile(translation_path):
            return f"Translation file {translation_path} not found", 404

        with open(translation_path, "r", encoding="utf-8") as f:
            translation_data = json.load(f)

        # Compose verses and translations
        verses = []
        for i in range(1, arabic_data.get("count", 0) + 1):
            key = f"verse_{i}"
            arabic_text = arabic_data["verse"].get(key, "")
            translation_text = translation_data["verse"].get(key, "")
            verses.append({"arabic": arabic_text, "translation": translation_text})

        # Audio file path (assumes mp3 named like 023-al-muminun.mp3 inside reciter folder)
        # For simplicity, we look for surah mp3 starting with surah number prefix
        recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
        prefix = f"{surah_num_int:03d}-"
        audio_file = None
        for f_name in os.listdir(recitation_folder):
            if f_name.startswith(prefix) and f_name.endswith(".mp3"):
                audio_file = f_name
                break

        if not audio_file:
            return f"Recitation audio for Surah {surah_num_int} not found", 404

        audio_url = f"/audio/{reciter}/{audio_file}"
        background_url = f"/backgrounds/{background}"

        # Simple HTML page with audio and verses
        html = """
        <html>
        <head>
          <title>Quran Video Proof of Concept</title>
          <style>
            body {
              background: black;
              color: white;
              font-family: 'Arial', sans-serif;
              text-align: center;
              background-size: cover;
              background-repeat: no-repeat;
              background-position: center;
            }
            .verse {
              margin: 20px;
              font-size: 20px;
            }
            .arabic {
              font-size: 30px;
              direction: rtl;
              margin-bottom: 5px;
              font-weight: bold;
            }
            .translation {
              font-style: italic;
            }
            audio {
              margin-top: 30px;
              width: 80%;
              outline: none;
            }
          </style>
        </head>
        <body style="background-image: url('{{ background_url }}')">
          <h1>Surah {{ surah_num }} - Reciter: {{ reciter }}</h1>
          <audio controls autoplay>
            <source src="{{ audio_url }}" type="audio/mpeg">
            Your browser does not support the audio element.
          </audio>
          <div id="verses">
            {% for v in verses %}
              <div class="verse">
                <div class="arabic">{{ v.arabic }}</div>
                <div class="translation">{{ v.translation }}</div>
              </div>
            {% endfor %}
          </div>
          <a href="/">Back</a>
        </body>
        </html>
        """

        # Render with Flask's built-in simple template engine
        return render_template_string(html,
                                      surah_num=surah_num_int,
                                      reciter=reciter,
                                      audio_url=audio_url,
                                      background_url=background_url,
                                      verses=verses)

    # GET method - show selection form
    form_html = """
    <html>
    <head>
      <title>Quran Video POC</title>
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

        <input type="submit" value="Create Video">
      </form>
    </body>
    </html>
    """

    return render_template_string(form_html,
                                  reciters=ALLOWED_RECITERS,
                                  backgrounds=ALLOWED_BACKGROUNDS)


@app.route("/audio/<reciter>/<filename>")
def serve_audio(reciter, filename):
    # Sanitize inputs a bit
    if reciter not in ALLOWED_RECITERS:
        abort(404)

    recitation_folder = os.path.join(RECITATIONS_DIR, reciter)
    file_path = os.path.join(recitation_folder, filename)

    if not os.path.isfile(file_path):
        abort(404)

    return send_file(file_path, mimetype="audio/mpeg")


@app.route("/backgrounds/<filename>")
def serve_background(filename):
    # Simple whitelist check
    if filename not in ALLOWED_BACKGROUNDS:
        abort(404)

    file_path = os.path.join(BACKGROUNDS_DIR, filename)
    if not os.path.isfile(file_path):
        abort(404)

    return send_file(file_path, mimetype="video/mp4")


if __name__ == "__main__":
    app.run(debug=True)
