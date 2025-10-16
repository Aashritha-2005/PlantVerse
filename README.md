---
title: PlantVerse AR
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.46.1"
app_file: app.py
pinned: false
---

# 🌿 PlantVerse AR

**Discover the plants around you — visually, geographically, and culturally.**  
PlantVerse AR is a multilingual, interactive Streamlit app that allows users to identify plants using AI and explore where they grow, why they thrive there, and what they're traditionally used for.

---

## ✨ Features

- 📷 **Plant Identifier:** Upload an image to identify the plant using AI  
- 🌐 **Multilingual UI:** Automatically translates plant info into Indian languages (e.g., Telugu, Hindi, Tamil)  
- 📖 **Wikipedia + Wikidata Insights:** Learn about taxonomy, medicinal uses, and plant hierarchy  
- 🗺️ **AR + Location Explorer:** Find where the plant naturally grows based on your location  
- 📌 **Nearby Observations:** Uses iNaturalist data to show where others have spotted the plant  
- 📦 **Export to JSON:** Download the results of your plant location search  

---

## 🛠️ How It Works

This app has two main modules:

### 1. Plant Identifier
- Upload a plant image
- AI model (from Hugging Face) predicts the species
- Wikipedia + Wikidata APIs fetch taxonomy and medicinal uses
- Translates results into your chosen language using Google Translate API

### 2. AR + Location-Based Explorer
- Detects your current location (or lets you enter it manually)
- Searches for nearby plant sightings using iNaturalist
- Displays nearby locations with photos, coordinates, and quality info

---

## 🚀 Run Locally

```bash
git clone https://huggingface.co/spaces/Aashritha05/PlantVerse
cd PlantVerse
pip install -r requirements.txt
streamlit run app.py

PlantVerse/
│
├── app.py                      # Streamlit entry-point
├── plant_identification.py     # Plant identification module
├── ar_location_plant_map.py    # Location + AR mapping module
├── requirements.txt            # Python dependencies
├── .huggingface.yml            # Hugging Face config (streamlit + app.py)
└── README.md                   # This file


---

✅ Just copy and paste this entire block into your `README.md` file, and it will pass validation.

Let me know if you'd like me to generate the `.huggingface.yml` file as well.
