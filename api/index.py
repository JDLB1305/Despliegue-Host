import sys, os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
from app import app

if __name__ == '__main__':
    # If running locally, enable debug mode and set host and port
    app.run(debug=True, host='0.0.0.0', port=5000)