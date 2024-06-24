import os
import json
import requests
from bs4 import BeautifulSoup

def split_polymaker_filament_name(raw_name):
    # Replace unicode hash with ASCII hash
    raw_name = raw_name.replace("⌗", "#")
    
    # Extract color and hex code
    color = raw_name.split("(")[0].strip()
    if "#" in raw_name:
        hex_code = raw_name[raw_name.index("#") + 1:raw_name.index("#")+7].lower()
    else:
        hex_code = "ffffff"
    
    filament_info = {
        "name": color,
        "hex": hex_code
    }
    
    return filament_info

def new_polymaker_color_array(raw_names):
    colors = []
    for name in raw_names:
        colors.append(split_polymaker_filament_name(name))
    return colors

def get_polymaker_colors(url):
    response = requests.get(url)
    html_content = response.text

    soup = BeautifulSoup(html_content, 'html.parser')

    elements = soup.select(".color-swatch__radio")

    values = [element["value"] for element in elements]
    return values

def read_json(file_path):
    with open(file_path, "r", encoding='utf-8') as file:
        return json.load(file)

def write_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def update_filament_color_by_name(data, name, new_color):
    for filament in data.get('filaments', []):
        if filament.get('name') == name:
            filament['colors'] = new_color
            break

def update_json_file_by_name(file_path, name, new_color):
    data = read_json(file_path)
    update_filament_color_by_name(data, name, new_color)
    write_json(file_path, data)

filaments = [
    {
        "name": "PolyTerra™ {color_name}",
        "colors": new_polymaker_color_array(get_polymaker_colors("https://us.polymaker.com/products/polyterra-pla"))
    },
]

#print(filaments)

for filament in filaments:
    update_json_file_by_name("filaments/polymaker.json", filament['name'], filament['colors'])
    print(f"Updated {filament['name']} in filaments.json")