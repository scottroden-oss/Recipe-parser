import sys
from os.path import dirname, abspath

# Add parent directory to Python path
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# Import Flask app
from app import app
