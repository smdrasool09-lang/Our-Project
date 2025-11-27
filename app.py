import os
import tempfile
import speech_recognition as sr

from flask import Flask, request, jsonify
from flask_cors import CORS
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

# Load environment variables (HOST, PORT, etc.) from .env file
load_dotenv()

app = Flask(__name__)
# Enable CORS for all origins, allowing your static index.html to communicate with the server
CORS(app)

# --- TEXT TRANSLATION ROUTE ---
@app.route("/translate", methods=["POST"])
def translate_text():
    # Initialize variables for safe access in return statement
    translated_en = None
    translated_te = None
    translated_ta = None
    text = None
    
    try:
        text = request.form.get("text")
        if not text:
            return jsonify({"error": "No text provided"}), 400

        # 1. English Translation (Fallback to original text if failed)
        translated_en = text
        try:
            translated_en = GoogleTranslator(source="auto", target="en").translate(text)
        except Exception:
            # If Google translation fails, translated_en remains the original text (text)
            pass

        # 2. Telugu and Tamil Translation (if these fail, they are caught by the outer 'except')
        translated_te = GoogleTranslator(source="auto", target="te").translate(text)
        translated_ta = GoogleTranslator(source="auto", target="ta").translate(text)

        return jsonify({
            "original": text,
            "translated": {
                "english": translated_en,
                "telugu": translated_te,
                "tamil": translated_ta
            }
        })
        
    except Exception as e:
        # Catch any errors from request parsing or translation calls
        return jsonify({"error": f"Text translation failed: {str(e)}"}), 500


# --- VOICE TRANSLATION ROUTE ---
@app.route("/voice", methods=["POST"])
def translate_voice():
    wav_path = None
    
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file"}), 400

        audio_file = request.files["audio"]
        
        # Save the audio file to a temporary WAV path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            audio_file.save(temp_wav.name)
            wav_path = temp_wav.name
        
        print(f"Audio file saved: {wav_path}")
        
        # Recognize speech
        r = sr.Recognizer()
        
        # Use a nested try/except for recognition errors specifically
        try:
            with sr.AudioFile(wav_path) as source:
                print("Reading audio file...")
                audio_data = r.record(source)
                print("Recognizing speech...")
                # Google Speech Recognition is a common default
                text = r.recognize_google(audio_data)
                print(f"Recognized: {text}")
        
        except sr.UnknownValueError:
            return jsonify({"error": "Could not understand audio. Please speak louder and clearer."}), 400
        except sr.RequestError as e:
            return jsonify({"error": f"Google Speech Recognition service error: {str(e)}. Check internet connection."}), 500
        
        # Translation of Recognized Text
        translated_te = GoogleTranslator(source="auto", target="te").translate(text)
        translated_ta = GoogleTranslator(source="auto", target="ta").translate(text)

        return jsonify({
            "original": text,
            "translated": {
                "english": text, # Recognized text is the English translation
                "telugu": translated_te,
                "tamil": translated_ta
            }
        })
        
    except Exception as e:
        # Catch generic errors (file saving, etc.)
        return jsonify({"error": f"Voice processing failed: {str(e)}"}), 500
        
    finally:
        # Crucial step: Ensure the temporary file is deleted even if an error occurs
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)


if __name__ == "__main__":
    print("Starting Flask server...")
    
    # Get configuration from .env file or use defaults
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("FLASK_DEBUG") == "1"

    app.run(debug=DEBUG, host=HOST, port=PORT)
    