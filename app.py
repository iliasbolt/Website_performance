from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app, origins="https://website-performance-front.onrender.com", support_credentials=True)

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', 'https://website-performance-front.onrender.com')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
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

        # Get the HTML content and its size
        html_content = response.content  # Read content once
        html_size_bytes = len(html_content)

        # Parse HTML to find external resources
        soup = BeautifulSoup(html_content, 'html.parser')
        total_size_bytes = html_size_bytes

        # Fetch and calculate sizes for all external assets
        for tag in soup.find_all(['img', 'link', 'script']):
            attr = 'src' if tag.name in ['img', 'script'] else 'href'
            resource_url = tag.get(attr)

            if resource_url:
                # Build absolute URL
                resource_url = urljoin(url, resource_url)

                try:
                    res = requests.get(resource_url, stream=True, timeout=5)
                    if res.status_code == 200:
                        total_size_bytes += sum(len(chunk) for chunk in res.iter_content(1024))
                except requests.RequestException:
                    continue  # Ignore failed requests for assets

        # Convert sizes to MB
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
