import folium
from backend.scrapers.synonyms import bundesliga_1_stadiums, bundesliga_2_stadiums, third_liga_stadiums

# Create map centered on Germany
map_bundesliga = folium.Map(location=[51.1657, 10.4515], zoom_start=6)

# Create feature groups for filtering
bundesliga_1_group = folium.FeatureGroup(name="Bundesliga 1").add_to(map_bundesliga)
bundesliga_2_group = folium.FeatureGroup(name="Bundesliga 2").add_to(map_bundesliga)
bundesliga_3_group = folium.FeatureGroup(name="3. Liga").add_to(map_bundesliga)
hbf_group = folium.FeatureGroup(name="Hauptbahnhöfe").add_to(map_bundesliga)

# Bundesliga 1 stadium markers (Red)
for stadium in bundesliga_1_stadiums:
    folium.Marker(
        location=stadium["stadium_location"],
        popup=f"<strong>{stadium['stadium']}</strong><br>{stadium['team']} (Bundesliga 1)",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(bundesliga_1_group)

    # Hauptbahnhof marker (Golden)
    folium.Marker(
        location=stadium["hbf"]["location"],
        popup=f"<strong>{stadium['hbf']['name']}</strong><br>Main Train Station for {stadium['team']}",
        icon=folium.Icon(color='orange', icon='cloud')
    ).add_to(hbf_group)

# Bundesliga 2 stadium markers (Blue)
for stadium in bundesliga_2_stadiums:
    folium.Marker(
        location=stadium["stadium_location"],
        popup=f"<strong>{stadium['stadium']}</strong><br>{stadium['team']} (Bundesliga 2)",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(bundesliga_2_group)

    # Hauptbahnhof marker (Golden)
    folium.Marker(
        location=stadium["hbf"]["location"],
        popup=f"<strong>{stadium['hbf']['name']}</strong><br>Main Train Station for {stadium['team']}",
        icon=folium.Icon(color='orange', icon='cloud')
    ).add_to(hbf_group)

# 3. Liga stadium markers (White)
for stadium in third_liga_stadiums:
    folium.Marker(
        location=stadium["stadium_location"],
        popup=f"<strong>{stadium['stadium']}</strong><br>{stadium['team']} (3. Liga)",
        icon=folium.Icon(color='black', icon='info-sign')
    ).add_to(bundesliga_3_group)

    # Hauptbahnhof marker (Golden)
    folium.Marker(
        location=stadium["hbf"]["location"],
        popup=f"<strong>{stadium['hbf']['name']}</strong><br>Main Train Station for {stadium['team']}",
        icon=folium.Icon(color='orange', icon='cloud')
    ).add_to(hbf_group)

# Add layer control to allow filtering
folium.LayerControl().add_to(map_bundesliga)

# Save map to HTML
map_bundesliga.save("bundesliga_all_leagues_stadiums_with_hbf_filter.html")
 
