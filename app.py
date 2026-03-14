from flask import Flask, render_template, request
import re
import os

app = Flask(__name__)

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

def parse_recipe(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    ingredients = []
    steps = []
    in_ingredients = True
    for line in lines:
        if re.match(r'^\d|\d+/\d+', line):
            ingredients.append(line)
        else:
            if ingredients and not steps:  # switch to steps after ingredients
                pass
            steps.append(line)
    # Simple: assume first lines with quantities are ingredients, rest steps
    # But to improve, perhaps look for keywords like "Ingredients" or "Steps"
    # For now, this rough version
    return ingredients, steps

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    recipe = request.form['recipe']
    original = int(request.form['original_servings'])
    desired = int(request.form['servings'])
    factor = desired / original if original else 1
    ingredients, steps = parse_recipe(recipe)
    scaled_ingredients = [scale_ingredient(ing, factor) for ing in ingredients]
    return render_template('result.html', ingredients=scaled_ingredients, steps=steps)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))