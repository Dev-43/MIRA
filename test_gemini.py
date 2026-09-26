import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY not found in .env")
else:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.8-flash")
        response = model.generate_content("Say: MIRA Gemini connected")
        print(response.text.strip())
    except Exception as e:
        print(f"Gemini API error: {e}")
