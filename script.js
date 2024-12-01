const API_URL = 'https://backend-2qtn.onrender.com/get_size';

document.getElementById('sizeCheckerForm').addEventListener('submit', async (e) => {
    e.preventDefault(); // Prevent the form from refreshing the page

    const url = document.getElementById('url').value; // Get the URL input
    document.getElementById('result').innerText = "Checking...";

    try {
        // Make a POST request to the backend
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', // Ensure the backend gets JSON
            },
            body: JSON.stringify({ url: url }) // Send the URL in JSON format
        });

        // Check if the response is okay (status code in the range 200–299)
        if (!response.ok) {
            const errorMessage = await response.text();
            throw new Error(`Server Error: ${response.status} ${response.statusText}\n${errorMessage}`);
        }

        const data = await response.json(); // Parse JSON from the response

        // Display the result or error based on the backend's response
        if (data.error) {
            document.getElementById('result').innerText = `Error: ${data.error}`;
        } else {
            document.getElementById('result').innerHTML = `
                <p>HTML Size: ${data.html_size_mb} MB</p>
                <p>Total Page Size: ${data.total_size_mb} MB</p>
            `;
        }
    } catch (error) {
        // Handle any unexpected errors
        document.getElementById('result').innerText = `An unexpected error occurred: ${error.message}`;
        console.error('Error:', error);
    }
});