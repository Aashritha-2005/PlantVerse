import streamlit as st
import requests
import json
import math
from typing import Dict, List, Optional, Tuple
import urllib.parse

# Configure Streamlit page
st.set_page_config(
    page_title="Plant Species Finder",
    page_icon="🌱",
    layout="wide"
)

class PlantLocationFinder:
    def __init__(self):
        self.inaturalist_base_url = "https://api.inaturalist.org/v1"
        self.wikipedia_base_url = "https://en.wikipedia.org/api/rest_v1"
        self.ipinfo_url = "http://ip-api.com/json"


    def get_user_location(self) -> Optional[Tuple[float, float]]:
        """Get user's approximate location using IP geolocation from ip-api.com."""
        try:
            response = requests.get(self.ipinfo_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                lat = data.get("lat")
                lon = data.get("lon")
                if lat is not None and lon is not None:
                    return lat, lon
                else:
                    st.error("Could not extract lat/lon from response.")
            else:
                st.error(f"Geolocation request failed with status code: {response.status_code}")
        except Exception as e:
            st.error(f"Could not auto-detect location: {e}")
        return None

    
    def search_plant_species(self, plant_name: str) -> Optional[Dict]:
        """Search for plant species in iNaturalist to get taxon ID."""
        try:
            url = f"{self.inaturalist_base_url}/taxa"
            params = {
                'q': plant_name,
                'rank': 'species',
                'is_active': 'true',
                'per_page': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    return data['results'][0]
        except Exception as e:
            st.error(f"Error searching for plant species: {e}")
        return None
    
    def get_plant_observations(self, taxon_id: int, lat: float, lon: float, radius: int = 50) -> List[Dict]:
        """Get plant observations from iNaturalist near the specified location."""
        try:
            url = f"{self.inaturalist_base_url}/observations"
            params = {
                'taxon_id': taxon_id,
                'lat': lat,
                'lng': lon,
                'radius': radius,
                'per_page': 50,
                'order': 'desc',
                'order_by': 'observed_on',
                'quality_grade': 'research,needs_id',
                'photos': 'true',
                'geo': 'true'
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
        except Exception as e:
            st.error(f"Error fetching observations: {e}")
        return []
    
    def get_wikipedia_summary(self, scientific_name: str) -> str:
        """Get plant description from Wikipedia."""
        try:
            # Clean up scientific name for Wikipedia search
            search_term = scientific_name.replace(' ', '_')
            url = f"{self.wikipedia_base_url}/page/summary/{urllib.parse.quote(search_term)}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('extract', 'No description available.')
            else:
                # Try alternative search
                search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
                alt_search = scientific_name.split()[0]  # Use genus name
                response = requests.get(f"{search_url}{urllib.parse.quote(alt_search)}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('extract', 'No description available.')
        except Exception as e:
            pass
        
        return "Description not available from Wikipedia."
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in kilometers."""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def format_observation_data(self, observations: List[Dict], user_lat: float, user_lon: float, 
                              plant_info: Dict, description: str) -> List[Dict]:
        """Format observation data for display."""
        formatted_data = []
        
        for obs in observations:
            if not obs.get('geojson') or not obs['geojson'].get('coordinates'):
                continue
                
            coords = obs['geojson']['coordinates']
            obs_lon, obs_lat = coords[0], coords[1]
            
            distance = self.calculate_distance(user_lat, user_lon, obs_lat, obs_lon)
            
            # Get location name from place_guess or coordinates
            location_name = obs.get('place_guess', f"Location ({obs_lat:.4f}, {obs_lon:.4f})")
            
            formatted_obs = {
                'location_name': location_name,
                'latitude': obs_lat,
                'longitude': obs_lon,
                'distance_km': round(distance, 2),
                'observed_on': obs.get('observed_on_string', 'Unknown date'),
                'quality_grade': obs.get('quality_grade', 'unknown'),
                'url': obs.get('uri', ''),
                'photos': [photo['url'] for photo in obs.get('photos', [])[:2]],  # First 2 photos
                'description': description,
                'scientific_name': plant_info.get('name', 'Unknown'),
                'common_name': plant_info.get('preferred_common_name', 'Unknown')
            }
            
            formatted_data.append(formatted_obs)
        
        # Sort by distance
        formatted_data.sort(key=lambda x: x['distance_km'])
        return formatted_data

def main():
    st.title("🌱 Plant Species Location Finder")
    st.markdown("Find nearby locations of specific plant species using real-time observation data.")
    
    finder = PlantLocationFinder()
    
    # Sidebar for inputs
    st.sidebar.header("Search Parameters")
    
    # Plant name input
    plant_name = st.sidebar.text_input(
        "Enter plant name (common or scientific):",
        value="Neem",
        help="e.g., Neem, Azadirachta indica, Oak, Rose"
    )
    
    # Location input options
    location_option = st.sidebar.radio(
        "Choose location method:",
        ["Auto-detect my location", "Enter coordinates manually"]
    )
    
    user_lat, user_lon = None, None
    
    if location_option == "Auto-detect my location":
        if st.sidebar.button("Detect My Location"):
            with st.spinner("Detecting your location..."):
                location = finder.get_user_location()
                if location:
                    user_lat, user_lon = location
                    st.sidebar.success(f"Location detected: {user_lat:.4f}, {user_lon:.4f}")
                else:
                    st.sidebar.error("Could not detect location. Please enter manually.")
    else:
        user_lat = st.sidebar.number_input("Latitude:", value=28.6139, format="%.6f")
        user_lon = st.sidebar.number_input("Longitude:", value=77.2090, format="%.6f")
    
    # Search radius
    radius = st.sidebar.slider("Search radius (km):", min_value=1, max_value=100, value=25)
    
    # Search button
    if st.sidebar.button("Find Plants", type="primary"):
        if not plant_name:
            st.error("Please enter a plant name.")
            return
        
        if user_lat is None or user_lon is None:
            st.error("Please provide your location.")
            return
        
        # Show search progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Search for plant species
        status_text.text("Searching for plant species...")
        progress_bar.progress(25)
        
        plant_info = finder.search_plant_species(plant_name)
        if not plant_info:
            st.error(f"Could not find plant species '{plant_name}'. Please try a different name.")
            return
        
        # Step 2: Get plant description
        status_text.text("Getting plant information...")
        progress_bar.progress(50)
        
        scientific_name = plant_info.get('name', plant_name)
        description = finder.get_wikipedia_summary(scientific_name)
        
        # Step 3: Get observations
        status_text.text("Finding nearby observations...")
        progress_bar.progress(75)
        
        observations = finder.get_plant_observations(
            plant_info['id'], user_lat, user_lon, radius
        )
        
        # Step 4: Format results
        status_text.text("Processing results...")
        progress_bar.progress(100)
        
        if not observations:
            st.warning(f"No observations of '{plant_name}' found within {radius}km of your location.")
            progress_bar.empty()
            status_text.empty()
            return
        
        # Format and display results
        formatted_results = finder.format_observation_data(
            observations, user_lat, user_lon, plant_info, description
        )
        
        progress_bar.empty()
        status_text.empty()
        
        # Display results
        st.success(f"Found {len(formatted_results)} observations of {plant_info.get('preferred_common_name', plant_name)}")
        
        # Plant information card
        st.subheader("Plant Information")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write(f"**Common Name:** {plant_info.get('preferred_common_name', 'Unknown')}")
            st.write(f"**Scientific Name:** {scientific_name}")
            st.write(f"**Rank:** {plant_info.get('rank', 'Unknown')}")
        
        with col2:
            st.write("**Description:**")
            st.write(description[:300] + "..." if len(description) > 300 else description)
        
        # Results
        st.subheader("Nearby Locations")
        
        for i, result in enumerate(formatted_results[:10]):  # Show top 10 results
            with st.expander(f"📍 {result['location_name']} - {result['distance_km']}km away"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write(f"**Distance:** {result['distance_km']} km")
                    st.write(f"**Coordinates:** {result['latitude']:.6f}, {result['longitude']:.6f}")
                    st.write(f"**Observed on:** {result['observed_on']}")
                    st.write(f"**Quality:** {result['quality_grade'].replace('_', ' ').title()}")
                    
                    if result['url']:
                        st.markdown(f"[View on iNaturalist]({result['url']})")
                
                with col2:
                    if result['photos']:
                        st.write("**Photos:**")
                        for photo_url in result['photos']:
                            try:
                                st.image(photo_url, width=200)
                            except:
                                st.write("Photo not available")
        
        # Export option
        if st.button("Export Results as JSON"):
            json_data = {
                'search_query': plant_name,
                'user_location': {'latitude': user_lat, 'longitude': user_lon},
                'search_radius_km': radius,
                'plant_info': plant_info,
                'results': formatted_results
            }
            
            st.download_button(
                label="Download JSON",
                data=json.dumps(json_data, indent=2),
                file_name=f"plant_locations_{plant_name.replace(' ', '_')}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()

# import streamlit as st
# import requests
# import json
# import math
# from typing import Dict, List, Optional, Tuple
# import urllib.parse

# # Configure Streamlit page
# st.set_page_config(
#     page_title="Plant Species Finder",
#     page_icon="🌱",
#     layout="wide"
# )

# class PlantLocationFinder:
#     def __init__(self):
#         self.inaturalist_base_url = "https://api.inaturalist.org/v1"
#         self.wikipedia_base_url = "https://en.wikipedia.org/api/rest_v1"
#         self.ipinfo_url = "http://ip-api.com/json"


#     def get_user_location(self) -> Optional[Tuple[float, float]]:
#         """Get user's approximate location using IP geolocation from ip-api.com."""
#         try:
#             response = requests.get(self.ipinfo_url, timeout=5)
#             if response.status_code == 200:
#                 data = response.json()
#                 lat = data.get("lat")
#                 lon = data.get("lon")
#                 if lat is not None and lon is not None:
#                     return lat, lon
#                 else:
#                     st.error("Could not extract lat/lon from response.")
#             else:
#                 st.error(f"Geolocation request failed with status code: {response.status_code}")
#         except Exception as e:
#             st.error(f"Could not auto-detect location: {e}")
#         return None

    
#     def search_plant_species(self, plant_name: str) -> Optional[Dict]:
#         """Search for plant species in iNaturalist to get taxon ID."""
#         try:
#             url = f"{self.inaturalist_base_url}/taxa"
#             params = {
#                 'q': plant_name,
#                 'rank': 'species',
#                 'is_active': 'true',
#                 'per_page': 1
#             }
            
#             response = requests.get(url, params=params, timeout=10)
#             if response.status_code == 200:
#                 data = response.json()
#                 if data['results']:
#                     return data['results'][0]
#         except Exception as e:
#             st.error(f"Error searching for plant species: {e}")
#         return None
    
#     def get_plant_observations(self, taxon_id: int, lat: float, lon: float, radius: int = 50) -> List[Dict]:
#         """Get plant observations from iNaturalist near the specified location."""
#         try:
#             url = f"{self.inaturalist_base_url}/observations"
#             params = {
#                 'taxon_id': taxon_id,
#                 'lat': lat,
#                 'lng': lon,
#                 'radius': radius,
#                 'per_page': 50,
#                 'order': 'desc',
#                 'order_by': 'observed_on',
#                 'quality_grade': 'research,needs_id',
#                 'photos': 'true',
#                 'geo': 'true'
#             }
            
#             response = requests.get(url, params=params, timeout=15)
#             if response.status_code == 200:
#                 data = response.json()
#                 return data.get('results', [])
#         except Exception as e:
#             st.error(f"Error fetching observations: {e}")
#         return []
    
#     def get_wikipedia_summary(self, scientific_name: str) -> str:
#         """Get plant description from Wikipedia."""
#         try:
#             # Clean up scientific name for Wikipedia search
#             search_term = scientific_name.replace(' ', '_')
#             url = f"{self.wikipedia_base_url}/page/summary/{urllib.parse.quote(search_term)}"
            
#             response = requests.get(url, timeout=10)
#             if response.status_code == 200:
#                 data = response.json()
#                 return data.get('extract', 'No description available.')
#             else:
#                 # Try alternative search
#                 search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
#                 alt_search = scientific_name.split()[0]  # Use genus name
#                 response = requests.get(f"{search_url}{urllib.parse.quote(alt_search)}", timeout=10)
#                 if response.status_code == 200:
#                     data = response.json()
#                     return data.get('extract', 'No description available.')
#         except Exception as e:
#             pass
        
#         return "Description not available from Wikipedia."
    
#     def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
#         """Calculate distance between two coordinates in kilometers."""
#         R = 6371  # Earth's radius in kilometers
        
#         lat1_rad = math.radians(lat1)
#         lat2_rad = math.radians(lat2)
#         delta_lat = math.radians(lat2 - lat1)
#         delta_lon = math.radians(lon2 - lon1)
        
#         a = (math.sin(delta_lat / 2) ** 2 + 
#              math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
#         c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
#         return R * c
    
#     def format_observation_data(self, observations: List[Dict], user_lat: float, user_lon: float, 
#                               plant_info: Dict, description: str) -> List[Dict]:
#         """Format observation data for display."""
#         formatted_data = []
        
#         for obs in observations:
#             if not obs.get('geojson') or not obs['geojson'].get('coordinates'):
#                 continue
                
#             coords = obs['geojson']['coordinates']
#             obs_lon, obs_lat = coords[0], coords[1]
            
#             distance = self.calculate_distance(user_lat, user_lon, obs_lat, obs_lon)
            
#             # Get location name from place_guess or coordinates
#             location_name = obs.get('place_guess', f"Location ({obs_lat:.4f}, {obs_lon:.4f})")
            
#             formatted_obs = {
#                 'location_name': location_name,
#                 'latitude': obs_lat,
#                 'longitude': obs_lon,
#                 'distance_km': round(distance, 2),
#                 'observed_on': obs.get('observed_on_string', 'Unknown date'),
#                 'quality_grade': obs.get('quality_grade', 'unknown'),
#                 'url': obs.get('uri', ''),
#                 'photos': [photo['url'] for photo in obs.get('photos', [])[:2]],  # First 2 photos
#                 'description': description,
#                 'scientific_name': plant_info.get('name', 'Unknown'),
#                 'common_name': plant_info.get('preferred_common_name', 'Unknown')
#             }
            
#             formatted_data.append(formatted_obs)
        
#         # Sort by distance
#         formatted_data.sort(key=lambda x: x['distance_km'])
#         return formatted_data

# def main():
#     st.title("🌱 Plant Species Location Finder")
#     st.markdown("Find nearby locations of specific plant species using real-time observation data.")
    
#     finder = PlantLocationFinder()
    
#     # Sidebar for inputs
#     st.sidebar.header("Search Parameters")
    
#     # Plant name input
#     plant_name = st.sidebar.text_input(
#         "Enter plant name (common or scientific):",
#         value="Neem",
#         help="e.g., Neem, Azadirachta indica, Oak, Rose"
#     )
    
#     # Location input options
#     location_option = st.sidebar.radio(
#         "Choose location method:",
#         ["Auto-detect my location", "Enter coordinates manually"]
#     )
    
#     user_lat, user_lon = None, None
    
#     if location_option == "Auto-detect my location":
#         if st.sidebar.button("Detect My Location"):
#             with st.spinner("Detecting your location..."):
#                 location = finder.get_user_location()
#                 if location:
#                     user_lat, user_lon = location
#                     st.sidebar.success(f"Location detected: {user_lat:.4f}, {user_lon:.4f}")
#                 else:
#                     st.sidebar.error("Could not detect location. Please enter manually.")
#     else:
#         user_lat = st.sidebar.number_input("Latitude:", value=28.6139, format="%.6f")
#         user_lon = st.sidebar.number_input("Longitude:", value=77.2090, format="%.6f")
    
#     # Search radius
#     radius = st.sidebar.slider("Search radius (km):", min_value=1, max_value=100, value=25)
    
#     # Search button
#     if st.sidebar.button("Find Plants", type="primary"):
#         if not plant_name:
#             st.error("Please enter a plant name.")
#             return
        
#         if user_lat is None or user_lon is None:
#             st.error("Please provide your location.")
#             return
        
#         # Show search progress
#         progress_bar = st.progress(0)
#         status_text = st.empty()
        
#         # Step 1: Search for plant species
#         status_text.text("Searching for plant species...")
#         progress_bar.progress(25)
        
#         plant_info = finder.search_plant_species(plant_name)
#         if not plant_info:
#             st.error(f"Could not find plant species '{plant_name}'. Please try a different name.")
#             return
        
#         # Step 2: Get plant description
#         status_text.text("Getting plant information...")
#         progress_bar.progress(50)
        
#         scientific_name = plant_info.get('name', plant_name)
#         description = finder.get_wikipedia_summary(scientific_name)
        
#         # Step 3: Get observations
#         status_text.text("Finding nearby observations...")
#         progress_bar.progress(75)
        
#         observations = finder.get_plant_observations(
#             plant_info['id'], user_lat, user_lon, radius
#         )
        
#         # Step 4: Format results
#         status_text.text("Processing results...")
#         progress_bar.progress(100)
        
#         if not observations:
#             st.warning(f"No observations of '{plant_name}' found within {radius}km of your location.")
#             progress_bar.empty()
#             status_text.empty()
#             return
        
#         # Format and display results
#         formatted_results = finder.format_observation_data(
#             observations, user_lat, user_lon, plant_info, description
#         )
        
#         progress_bar.empty()
#         status_text.empty()
        
#         # Display results
#         st.success(f"Found {len(formatted_results)} observations of {plant_info.get('preferred_common_name', plant_name)}")
        
#         # Plant information card
#         st.subheader("Plant Information")
#         col1, col2 = st.columns([1, 2])
        
#         with col1:
#             st.write(f"**Common Name:** {plant_info.get('preferred_common_name', 'Unknown')}")
#             st.write(f"**Scientific Name:** {scientific_name}")
#             st.write(f"**Rank:** {plant_info.get('rank', 'Unknown')}")
        
#         with col2:
#             st.write("**Description:**")
#             st.write(description[:300] + "..." if len(description) > 300 else description)
        
#         # Results
#         st.subheader("Nearby Locations")
        
#         for i, result in enumerate(formatted_results[:10]):  # Show top 10 results
#             with st.expander(f"📍 {result['location_name']} - {result['distance_km']}km away"):
#                 col1, col2 = st.columns([1, 1])
                
#                 with col1:
#                     st.write(f"**Distance:** {result['distance_km']} km")
#                     st.write(f"**Coordinates:** {result['latitude']:.6f}, {result['longitude']:.6f}")
#                     st.write(f"**Observed on:** {result['observed_on']}")
#                     st.write(f"**Quality:** {result['quality_grade'].replace('_', ' ').title()}")
                    
#                     if result['url']:
#                         st.markdown(f"[View on iNaturalist]({result['url']})")
                
#                 with col2:
#                     if result['photos']:
#                         st.write("**Photos:**")
#                         for photo_url in result['photos']:
#                             try:
#                                 st.image(photo_url, width=200)
#                             except:
#                                 st.write("Photo not available")
        
#         # Export option
#         if st.button("Export Results as JSON"):
#             json_data = {
#                 'search_query': plant_name,
#                 'user_location': {'latitude': user_lat, 'longitude': user_lon},
#                 'search_radius_km': radius,
#                 'plant_info': plant_info,
#                 'results': formatted_results
#             }
            
#             st.download_button(
#                 label="Download JSON",
#                 data=json.dumps(json_data, indent=2),
#                 file_name=f"plant_locations_{plant_name.replace(' ', '_')}.json",
#                 mime="application/json"
#             )

# if __name__ == "__main__":
#     main()
