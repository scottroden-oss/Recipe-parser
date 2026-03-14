from flask import Flask, render_template, request
import re
import os
import json
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def fetch_recipe(url):
    try:
        response = requests.get(url, timeout=10)
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
    ingredients = data.get('recipeIngredient', [])
    instructions = [step.get('text', '') if isinstance(step, dict) else str(step) for step in data.get('recipeInstructions', [])]
    servings = data.get('recipeYield', 4)
    if isinstance(servings, str):
        servings = int(re.search(r'\d+', servings).group()) if re.search(r'\d+', servings) else 4
    return servings, ingredients, instructions

def parse_recipe_html(soup):
    # Simple fallback: look for lists
    ingredients = []
    instructions = []
    servings = 4  # default
    
    # Look for servings
    servings_text = soup.find(text=re.compile(r'serves?|yield', re.I))
    if servings_text:
        match = re.search(r'\d+', servings_text)
        if match:
            servings = int(match.group())
    
    # Ingredients: look for ul or ol with class containing 'ingredient'
    ing_list = soup.find(['ul', 'ol'], class_=re.compile(r'ingredient', re.I))
    if ing_list:
        ingredients = [li.get_text(strip=True) for li in ing_list.find_all('li')]
    
    # Instructions
    inst_list = soup.find(['ul', 'ol'], class_=re.compile(r'instruction|step|method', re.I))
    if inst_list:
        instructions = [li.get_text(strip=True) for li in inst_list.find_all('li')]
    
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

def scale_ingredient(ingredient, factor):
    qty, rest = parse_quantity(ingredient)
    if qty is not None:
        new_qty = qty * factor
        # Format as decimal for simplicity
        return f"{new_qty:.2f} {rest}"
    return ingredient

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    url = request.form['url']
    original_servings, ingredients, steps = fetch_recipe(url)
    if original_servings is None:
        return render_template('error.html', error=steps)  # steps is error message
    return render_template('result.html', ingredients=ingredients, steps=steps, original_servings=original_servings)

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