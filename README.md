# SmartFarm — AI Crop Advisor for Indian Farmers

SmartFarm is a responsive, AI-powered agricultural diagnostic dashboard designed for Indian farmers. The application allows farmers to input crop descriptions, speak queries, or upload photos to instantly receive detailed crop disease diagnoses, immediate treatment steps, localized weather warnings, and expert helpline details.

---

## 📋 Problem Statement

Manual diagnosis of crop disease is slow, error-prone, and inaccessible to many rural Indian farmers, often leading to delayed intervention and significant crop loss. SmartFarm resolves this by providing a high-performance, easy-to-use AI advisory interface that integrates multimodal diagnosis (images + text), Hindi speech-to-text, weather patterns, and printable report downloads.

---

## ⚡ Features

1. **Multimodal AI Diagnosis**: Analyzes a farmer's written query combined with an uploaded crop photo (using the Gemini API) to generate crop disease insights.
2. **Interactive Voice Input**: Employs the browser Web Speech API for voice transcription, supporting Hindi (`hi-IN`) and English (`en-IN`) text area population.
3. **Live Weather Integration**: Detects city or district names in the farmer's query, fetches real-time parameters from Open-Meteo API, and flags weather anomalies (high temperature/humidity) favorable to disease spread.
4. **Devanagari Hindi Translation**: Farmers can translate English diagnoses into Devanagari Hindi at the click of a button.
5. **Interactive Severity Progress bar**: Dynamically updates colors (Low, Medium, High, Critical) and length based on the crop disease severity level.
6. **Local History Logs**: Saves the last 20 queries locally in `history.json`, displaying them as clickable recent logs in the sidebar.
7. **Report Exports**: Generates formatted PDF advisory reports using ReportLab for local download.
8. **Kisan Call Center Integration**: Connects farmers directly to the Kisan Call Center hotline (1800-180-1551) for immediate expert support.

---

## 🛠️ Tech Stack

* **Backend**: Python 3, Flask
* **API Integration**: Gemini SDK (`google-genai`), Open-Meteo Weather API
* **Document Processing**: ReportLab (PDF generation), Pillow (Image processing)
* **Frontend**: HTML5 (Semantic elements), Vanilla CSS3 (Custom properties, Glassmorphism, CSS variables), Vanilla JavaScript
* **Voice API**: HTML5 Web Speech API

---

## 🚀 How to Run Locally

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Configure Environment Variables
Create a `.env` file in the root directory and add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Dependencies
Install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Start the Application
Run the Flask server:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000/`.

---

## 📸 Screenshots

* **Homepage**:
  ![SmartFarm Home Page Mockup](static/css/style.css) *(Placeholder: Refer to `/redesigned_homepage_1782907279167.png` in the artifacts directory for actual redesigned visual layouts).*
* **Advisory Report**:
  ![SmartFarm Report Preview](static/css/style.css) *(Placeholder: Refer to `/diagnosis_card_bottom_and_helpline_1782907369868.png` for advisory results and helpline gradient).*

---

## 🏆 Kaggle Competition References

The modeling dataset and design concepts are inspired by public Kaggle agricultural challenges:
* **Rice Paddy Disease Classification**: [Paddy Doctor Paddy Disease Classification Competition](https://www.kaggle.com/competitions/paddy-disease-classification)
* **Indian Crop Dataset**: [Top Agriculture Crop Disease India Dataset](https://www.kaggle.com/datasets/vigneshwaransivalingam/top-agriculture-crop-images-india)
* **Sugarcane & Leaf Disease Dataset**: [Master Plant Disease Dataset](https://www.kaggle.com/datasets/vipoooool/plant-disease-detection-dataset)
