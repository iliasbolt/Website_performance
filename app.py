from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)
cors = CORS(app)

@app.after_request
def add_cors_headers(response):
    response  = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response


@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        # Parse the incoming JSON request
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "URL is required"}), 400

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        # Fetch the HTML content of the main URL
        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()

        # Read the HTML content and its size
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))  # Convert to bytes for size calculation

        # Use Beautiful Soup to parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Initialize the total size with the HTML size
        total_size_bytes = html_size_bytes

        # List of tags and their attributes for external resources
        resource_tags = {
            'img': 'src',
            'script': 'src',
            'link': 'href'
        }

        # Loop through each tag and fetch the resources
        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)  # Ensure full URL for resource

                    try:
                        # Fetch the resource
                        resource_response = requests.get(full_url, timeout=5, stream=True)
                        resource_response.raise_for_status()

                        # Calculate the size of the resource
                        total_size_bytes += sum(len(chunk) for chunk in resource_response.iter_content(1024))
                    except requests.RequestException:
                        # Skip any resources that fail to fetch
                        continue

        # Convert sizes to MB
        html_size_mb = round(html_size_bytes / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        # Return the results
        return jsonify({
            "html_size_mb": html_size_mb,
            "total_size_mb": total_size_mb
        })

    except requests.RequestException as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)