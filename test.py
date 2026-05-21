import google.generativeai as genai

genai.configure(api_key="AIzaSyDNa0g7eOrdxW2GseZk6VfoQvYwQ6eWVU0")

model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content("Hello")

print(response.text)