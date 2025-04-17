import google.generativeai as genai

google_api_key = "AIzaSyBQrTJFsVZ_Ydn5O8opGqL0MfZrVaCDj_U"
genai.configure(api_key=google_api_key)
gemini_model = genai.GenerativeModel("gemini-pro")

for m in genai.list_models():
    print(m.name)