# Recipe Parser and Scaler

A Flask web app that parses raw recipe text to extract ingredients and steps, and scales ingredients based on the number of servings.

## Features

- Paste any recipe text (with ads, spacing, etc.)
- Automatically extracts ingredients and steps
- Scales ingredient quantities for different serving sizes

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python app.py`
3. Open http://localhost:5000 in your browser

## Usage

1. Paste the recipe text into the textarea.
2. Enter the desired number of servings.
3. Click "Parse and Scale" to see the cleaned ingredients and steps.