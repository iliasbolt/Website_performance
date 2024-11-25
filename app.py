from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        # Make a request to the URL
        response = requests.get(url, stream=True)

        # Ensure the response is valid
        if response.status_code != 200:
            return jsonify({"error": f"Failed to fetch URL (status: {response.status_code})"}), 400

        # Calculate total size in bytes
        total_size_bytes = sum(len(chunk) for chunk in response.iter_content(1024))
        print('Size == > '+ total_size_bytes)

        # Convert to MB (1 MB = 1024 * 1024 bytes)
        size_mb = round(total_size_bytes / (1024 * 1024), 2)
        print('Size Return == > '+ size_mb)
        return jsonify({"size_mb": size_mb})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
