import streamlit as st
from plant_identification import main as plant_identifier_main
from ar_location_plant_map import main as ar_location_main

# Sidebar Navigation
st.sidebar.title("🌱 PlantVerse Navigation")
app_choice = st.sidebar.radio("Select Module:", ["Plant Identifier", "AR + Location Explorer"])

# App Navigation Logic
if app_choice == "Plant Identifier":
    st.title("📸 Plant Identifier")
    plant_identifier_main()
elif app_choice == "AR + Location Explorer":
    st.title("🗺️ AR + Location-Based Plant Map")
    ar_location_main()
