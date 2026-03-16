from flask import Flask, render_template, request
import re
import os
import json
import requests
import random
from bs4 import BeautifulSoup

app = Flask(__name__)

# Famous chef quotes for encouragement
CHEF_QUOTES = [
    {"chef": "Gordon Ramsay", "emoji": "👨‍🍳", "quote": "This is your chance to make something spectacular. Don't mess it up!"},
    {"chef": "Gordon Ramsay", "emoji": "👨‍🍳", "quote": "Come on! Put some heart into it! This dish deserves passion!"},
    {"chef": "Gordon Ramsay", "emoji": "👨‍🍳", "quote": "Beautiful! Now keep that momentum going!"},
    {"chef": "Julia Child", "emoji": "👩‍🍳", "quote": "You're doing wonderfully! Remember, no one's watching your mistakes."},
    {"chef": "Julia Child", "emoji": "👩‍🍳", "quote": "The only time to eat diet food is while you're waiting for the steak to cook!"},
    {"chef": "Anthony Bourdain", "emoji": "😎", "quote": "Skills can be taught. Character you either have or you don't have."},
    {"chef": "Jacques Pépin", "emoji": "👨‍🍳", "quote": "You're doing great! Cooking is about technique, not perfection."},
    {"chef": "Ina Garten", "emoji": "👩‍🍳", "quote": "How easy is that? You've got this!"},
    {"chef": "Jamie Oliver", "emoji": "👨‍🍳", "quote": "Lovely! Just lovely! Keep up the good work!"},
    {"chef": "Bobby Flay", "emoji": "🔥", "quote": "Bold flavors require bold confidence. You're crushing it!"},
]

def get_random_chef_quote():
    """Get a random encouraging chef quote"""
    return random.choice(CHEF_QUOTES)

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
                # Check if data is a list
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Recipe':
                            return parse_recipe_json(item)
                # Check if data has @graph (common pattern)
                elif '@graph' in data:
                    for item in data['@graph']:
                        if item.get('@type') == 'Recipe':
                            return parse_recipe_json(item)
                # Check if data itself is a Recipe
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

    # Handle different recipeYield formats
    if isinstance(servings, list):
        # Try to find a number in the list
        for item in servings:
            if isinstance(item, (int, float)):
                servings = int(item)
                break
            elif isinstance(item, str):
                match = re.search(r'\d+', item)
                if match:
                    servings = int(match.group())
                    break
        else:
            servings = 4  # default if nothing found
    elif isinstance(servings, str):
        servings = int(re.search(r'\d+', servings).group()) if re.search(r'\d+', servings) else 4
    elif not isinstance(servings, (int, float)):
        servings = 4
    else:
        servings = int(servings)

    image = data.get('image', '')
    if isinstance(image, list):
        image = image[0] if image else ''
    elif isinstance(image, dict):
        image = image.get('url', '')
    cook_time = parse_duration(data.get('cookTime', ''))
    prep_time = parse_duration(data.get('prepTime', ''))
    return servings, ingredients, instructions, image, cook_time, prep_time

def parse_recipe_html(soup):
    # Simple fallback: look for lists
    ingredients = []
    instructions = []
    servings = 4  # default
    image = ''
    cook_time = ''
    prep_time = ''

    # Look for servings - be smarter about finding the actual value
    servings = 4  # default

    # Try specific servings elements first (avoid adjustment buttons)
    servings_elem = soup.find('span', class_=re.compile(r'^wprm-recipe-servings\b', re.I))
    if not servings_elem:
        servings_elem = soup.find(['span', 'div'], class_=re.compile(r'recipe-servings(?!.*adjust)', re.I))
    if not servings_elem:
        servings_elem = soup.find(['span', 'div', 'p'], class_=re.compile(r'yield', re.I))

    if servings_elem:
        # Avoid picking up adjustment buttons (1x, 2x, 3x)
        text = servings_elem.get_text(strip=True)
        # Skip if it looks like adjustment buttons (e.g., "1x2x3x")
        if not re.search(r'\d+x\d+x', text):
            match = re.search(r'\d+', text)
            if match:
                servings = int(match.group())

    # Fallback: search in text
    if servings == 4:
        servings_text = soup.find(text=re.compile(r'serves?\s*\d+|yield\s*:?\s*\d+', re.I))
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
    # Try fraction first, then mixed number, then whole number
    match = re.match(r'(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)', ingredient.strip())
    if match:
        qty_str = match.group(1)
        if '/' in qty_str:
            parts = qty_str.split()
            if len(parts) == 1:
                # Just a fraction like "1/2"
                num, den = map(int, parts[0].split('/'))
                qty = num / den
            else:
                # Mixed number like "1 1/2"
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

def parse_duration(duration_str):
    """Convert ISO 8601 duration (e.g., PT15M, PT1H30M) to readable format"""
    if not duration_str or not isinstance(duration_str, str):
        return ''

    # Match PT[hours]H[minutes]M[seconds]S pattern
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    seconds = re.search(r'(\d+)S', duration_str)

    parts = []
    if hours:
        h = int(hours.group(1))
        parts.append(f"{h} hr" if h == 1 else f"{h} hrs")
    if minutes:
        m = int(minutes.group(1))
        parts.append(f"{m} min")
    if seconds and not (hours or minutes):  # Only show seconds if no hours/minutes
        s = int(seconds.group(1))
        parts.append(f"{s} sec")

    return ' '.join(parts) if parts else ''

def scale_ingredient(ingredient, factor):
    """Scale ingredient quantities by a factor"""
    qty, rest = parse_quantity(ingredient)
    if qty is None:
        return ingredient  # No quantity found, return as-is

    scaled_qty = qty * factor

    # Format the scaled quantity nicely
    if scaled_qty == int(scaled_qty):
        # Whole number
        qty_str = str(int(scaled_qty))
    elif abs(scaled_qty % 0.25) < 0.01:
        # Quarter fractions (includes halves)
        whole = int(scaled_qty)
        frac = scaled_qty - whole

        if abs(frac - 0.25) < 0.01:
            frac_str = "1/4"
        elif abs(frac - 0.5) < 0.01:
            frac_str = "1/2"
        elif abs(frac - 0.75) < 0.01:
            frac_str = "3/4"
        else:
            frac_str = ""

        if whole == 0:
            qty_str = frac_str
        elif frac_str:
            qty_str = f"{whole} {frac_str}"
        else:
            qty_str = str(whole)
    elif abs(scaled_qty % (1/3)) < 0.02:  # Close to 1/3
        # Third fractions
        whole = int(scaled_qty)
        frac = scaled_qty - whole

        if abs(frac - 1/3) < 0.02:
            frac_str = "1/3"
        elif abs(frac - 2/3) < 0.02:
            frac_str = "2/3"
        else:
            frac_str = ""

        if whole == 0 and frac_str:
            qty_str = frac_str
        elif frac_str:
            qty_str = f"{whole} {frac_str}"
        else:
            qty_str = str(whole)
    else:
        # Round to 2 decimal places
        qty_str = f"{scaled_qty:.2f}".rstrip('0').rstrip('.')

    return f"{qty_str} {rest}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    url = request.form['url']
    original_servings, ingredients, steps, image, cook_time, prep_time = fetch_recipe(url)
    if original_servings is None:
        return render_template('error.html', error=steps)  # steps is error message

    # Add chef quotes throughout the recipe
    chef_quotes = [get_random_chef_quote() for _ in range(3)]  # Get 3 random quotes

    return render_template('result.html', ingredients=ingredients, steps=steps,
                         original_servings=original_servings, image=image,
                         cook_time=cook_time, prep_time=prep_time, chef_quotes=chef_quotes)

@app.route('/scale', methods=['POST'])
def scale():
    ingredients_str = request.form['ingredients']
    steps_str = request.form.get('steps', '[]')

    # Parse JSON arrays
    try:
        ingredients = json.loads(ingredients_str)
        steps = json.loads(steps_str)
    except json.JSONDecodeError:
        ingredients = []
        steps = []

    original_servings = int(request.form['original_servings'])
    new_servings = int(request.form['new_servings'])
    factor = new_servings / original_servings if original_servings else 1
    scaled_ingredients = [scale_ingredient(ing, factor) for ing in ingredients]

    # Add chef quotes
    chef_quotes = [get_random_chef_quote() for _ in range(3)]

    return render_template('scaled_result.html', ingredients=scaled_ingredients,
                         steps=steps, servings=new_servings, chef_quotes=chef_quotes)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))