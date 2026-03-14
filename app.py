from flask import Flask, render_template, request
import re
import os
import json
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def fetch_recipe(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Recipe':
                            return parse_recipe_json(item)
                elif data.get('@type') == 'Recipe':
                    return parse_recipe_json(data)
            except json.JSONDecodeError:
                continue
        
        # Fallback: simple HTML parsing
        return parse_recipe_html(soup)
    except Exception as e:
        return None, [], [], str(e)

def parse_recipe_json(data):
    ingredients = [format_ingredient(ing) for ing in data.get('recipeIngredient', [])]
    instructions = [step.get('text', '') if isinstance(step, dict) else str(step) for step in data.get('recipeInstructions', [])]
    servings = data.get('recipeYield', 4)
    if isinstance(servings, str):
        servings = int(re.search(r'\d+', servings).group()) if re.search(r'\d+', servings) else 4
    image = data.get('image', '')
    if isinstance(image, list):
        image = image[0] if image else ''
    elif isinstance(image, dict):
        image = image.get('url', '')
    cook_time = data.get('cookTime', '')
    prep_time = data.get('prepTime', '')
    return servings, ingredients, instructions, image, cook_time, prep_time

def parse_recipe_html(soup):
    # Simple fallback: look for lists
    ingredients = []
    instructions = []
    servings = 4  # default
    image = ''
    cook_time = ''
    prep_time = ''
    
    # Look for servings
    servings = 4  # default
    # Try to find elements with servings info
    servings_elem = soup.find(['span', 'div', 'p'], class_=re.compile(r'servings?|yield', re.I))
    if servings_elem:
        text = servings_elem.get_text()
        match = re.search(r'\d+', text)
        if match:
            servings = int(match.group())
    else:
        # Fallback: search in text
        servings_text = soup.find(text=re.compile(r'serves?\s*\d+|yield\s*\d+', re.I))
        if servings_text:
            match = re.search(r'\d+', servings_text)
            if match:
                servings = int(match.group())
    
    # Ingredients: look for li with class containing 'ingredient'
    ing_items = soup.find_all('li', class_=re.compile(r'ingredient', re.I))
    if ing_items:
        ingredients = [format_ingredient(li.get_text(strip=True)) for li in ing_items]
    else:
        # Fallback: look for ul/ol with class containing 'ingredient'
        ing_list = soup.find(['ul', 'ol'], class_=re.compile(r'ingredient', re.I))
        if ing_list:
            ingredients = [format_ingredient(li.get_text(strip=True)) for li in ing_list.find_all('li')]
    
    # Instructions: look for li with class containing 'instruction' or 'step'
    inst_items = soup.find_all('li', class_=re.compile(r'instruction|step|method', re.I))
    if inst_items:
        instructions = [li.get_text(strip=True) for li in inst_items]
    else:
        # Fallback
        inst_list = soup.find(['ul', 'ol'], class_=re.compile(r'instruction|step|method', re.I))
        if inst_list:
            instructions = [li.get_text(strip=True) for li in inst_list.find_all('li')]
    
    return servings, ingredients, instructions, image, cook_time, prep_time
    
def parse_quantity(ingredient):
    # Match quantity at the start: whole number, fraction, or mixed
    match = re.match(r'(\d+(?:\s+\d+/\d+)?|\d+/\d+)', ingredient.strip())
    if match:
        qty_str = match.group(1)
        if '/' in qty_str:
            parts = qty_str.split()
            if len(parts) == 1:
                num, den = map(int, parts[0].split('/'))
                qty = num / den
            else:
                whole = int(parts[0])
                num, den = map(int, parts[1].split('/'))
                qty = whole + num / den
        else:
            qty = float(qty_str)
        rest = ingredient[match.end():].strip()
        return qty, rest
    return None, ingredient.strip()

def format_ingredient(ingredient):
    # Add space between quantity and unit if missing
    # Pattern: number followed by letters
    ingredient = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', ingredient)
    # Also handle fractions like 1/2cup -> 1/2 cup
    ingredient = re.sub(r'(\d/\d)([a-zA-Z])', r'\1 \2', ingredient)
    return ingredient

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    url = request.form['url']
    original_servings, ingredients, steps, image, cook_time, prep_time = fetch_recipe(url)
    if original_servings is None:
        return render_template('error.html', error=steps)  # steps is error message
    return render_template('result.html', ingredients=ingredients, steps=steps, original_servings=original_servings, image=image, cook_time=cook_time, prep_time=prep_time)

@app.route('/scale', methods=['POST'])
def scale():
    ingredients_str = request.form['ingredients']
    ingredients = ingredients_str.split(',')
    original_servings = int(request.form['original_servings'])
    new_servings = int(request.form['new_servings'])
    factor = new_servings / original_servings if original_servings else 1
    scaled_ingredients = [scale_ingredient(ing, factor) for ing in ingredients]
    steps = []  # not needed here
    return render_template('scaled_result.html', ingredients=scaled_ingredients, steps=steps, servings=new_servings)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))