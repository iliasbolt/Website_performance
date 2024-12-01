const API_URL = 'https://backend-2qtn.onrender.com/get_size';

document.getElementById('sizeCheckerForm').addEventListener('submit', async (e) => {
    e.preventDefault(); // Prevent the form from refreshing the page

    const url = document.getElementById('url').value.trim(); // Get and trim the URL input
    const resultElement = document.getElementById('result');
    resultElement.innerText = "Checking...";

    try {
        // Make a POST request to the backend
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', // Ensure the backend gets JSON
            },
            body: JSON.stringify({ url }) // Send the URL in JSON format
        });

        // Check if the response is okay
        if (!response.ok) {
            const errorMessage = await response.text();
            throw new Error(`Server Error: ${response.status} ${response.statusText}\n${errorMessage}`);
        }

        const data = await response.json(); // Parse JSON from the response

        // Handle backend errors
        if (data.error) {
            resultElement.innerText = `Error: ${data.error}`;
        } else {
            // Construct the HTML to show the aggregated results
            const resultHTML = `
                <p><strong>HTML Size:</strong> ${data.html_size_mb} MB</p>
                <p><strong>Images Size:</strong> ${data.images_size_mb} MB</p>
                <p><strong>CSS Size:</strong> ${data.css_size_mb} MB</p>
                <p><strong>JavaScript Size:</strong> ${data.js_size_mb} MB</p>
                <p><strong>External Resources Size:</strong> ${data.external_size_mb} MB</p>
                <p><strong>Total Page Size:</strong> ${data.total_size_mb} MB</p>
            `;

            // Update the result container with the aggregated results
            resultElement.innerHTML = resultHTML;
        }
    } catch (error) {
        // Display any unexpected errors
        resultElement.innerText = `An unexpected error occurred: ${error.message}`;
        console.error('Error:', error);
    }
});
