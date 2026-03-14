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

## Deployment

To deploy this app online:

### Option 1: Heroku (Free tier available)

1. Sign up for a Heroku account at https://heroku.com
2. Install Heroku CLI: `brew install heroku/brew/heroku` (or download from https://devcenter.heroku.com/articles/heroku-cli)
3. Login: `heroku login`
4. Create app: `heroku create your-app-name`
5. Push to Heroku: `git push heroku main`
6. Open: `heroku open`

### Option 2: PythonAnywhere (Free tier)

1. Sign up at https://www.pythonanywhere.com
2. Upload the files to a new web app.
3. Set the WSGI file to point to your app.

### Option 3: Vercel

1. Push to GitHub.
2. Connect to Vercel and deploy as Python app.