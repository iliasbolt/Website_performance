from flask import Flask, request, jsonify
from flask_cors import CORS  # Importing CORS module
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

# CORS configuration for the backend
CORS(app, origins="https://frontend-pdxs.onrender.com", supports_credentials=True)  # Allowing only the frontend URL

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'https://frontend-pdxs.onrender.com'  # Your frontend URL
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    if request.method == 'OPTIONS':  # Handling pre-flight OPTIONS requests
        response.status_code = 200
    return response

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "URL is required"}), 400

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

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
                    res = requests.get(resource_url, stream=True, timeout=10)
                    if res.status_code == 200:
                        total_size_bytes += sum(len(chunk) for chunk in res.iter_content(1024))
                except requests.RequestException:
                    continue

        html_size_mb = round(html_size_bytes / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        return jsonify({
            "html_size_mb": html_size_mb,
            "total_size_mb": total_size_mb
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)