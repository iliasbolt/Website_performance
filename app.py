from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

app = Flask(__name__)

# Configure logger
logging.basicConfig(level=logging.DEBUG)

# Allow CORS for frontend URL
CORS(app, origins="https://frontend-pdxs.onrender.com", support_credentials=True)

@app.after_request
def add_cors_headers(response):
    # Ensure all responses allow CORS for the frontend
    response.headers['Access-Control-Allow-Origin'] = 'https://frontend-pdxs.onrender.com'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    if request.method == 'OPTIONS':
        response.status_code = 200
    return response

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        # Get JSON data from the frontend
        data = request.get_json()  # This parses the JSON body
        url = data.get('url')

        if not url:
            return jsonify({"error": "URL is required"}), 400

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return jsonify({"error": "Invalid URL format."}), 400

        logging.debug(f"Fetching URL: {url}")

        # Fetch the main HTML document
        response = requests.get(url)
        if response.status_code != 200:
            return jsonify({"error": f"Failed to fetch URL (status: {response.status_code})"}), 400

        html_content = response.content
        html_size_bytes = len(html_content)
        soup = BeautifulSoup(html_content, 'html.parser')
        total_size_bytes = html_size_bytes

        # Fetch external resources and calculate total size
        for tag in soup.find_all(['img', 'link', 'script']):
            attr = 'src' if tag.name in ['img', 'script'] else 'href'
            resource_url = tag.get(attr)

            if resource_url:
                resource_url = urljoin(url, resource_url)
                try:
                    res = requests.get(resource_url, stream=True, timeout=5)
                    if res.status_code == 200:
                        total_size_bytes += sum(len(chunk) for chunk in res.iter_content(1024))
                    else:
                        logging.warning(f"Failed to fetch resource {resource_url}: {res.status_code}")
                except requests.RequestException as e:
                    logging.error(f"Error fetching resource {resource_url}: {str(e)}")
                    continue

        html_size_mb = round(html_size_bytes / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        logging.debug(f"HTML Size (MB): {html_size_mb}")
        logging.debug(f"Total Size (MB): {total_size_mb}")

        return jsonify({
            "html_size_mb": html_size_mb,
            "total_size_mb": total_size_mb
        })

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
