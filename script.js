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
            // Construct the HTML to show the results
            let resultHTML = `
                <p>HTML Size: ${data.html_size_mb} MB</p>
                <p>Images Size: ${data.images_size_mb} MB</p>
                <p>CSS Size: ${data.css_size_mb} MB</p>
                <p>JavaScript Size: ${data.js_size_mb} MB</p>
                <p>External Resources Size: ${data.external_size_mb} MB</p>
                <p>Total Page Size: ${data.total_size_mb} MB</p>
                <h3>Image Resources</h3>
                <ul>`;
                
            // List the image resources
            /*data.images.forEach(image => {
                resultHTML += `<li><a href="${image.url}" target="_blank">${image.url}</a> - ${image.size} bytes</li>`;
            });

            resultHTML += `</ul>
                <h3>CSS Resources</h3>
                <ul>`;
                
            // List the CSS resources
            data.css.forEach(css => {
                resultHTML += `<li><a href="${css.url}" target="_blank">${css.url}</a> - ${css.size} bytes</li>`;
            });

            resultHTML += `</ul>
                <h3>JavaScript Resources</h3>
                <ul>`;
                
            // List the JS resources
            data.js.forEach(js => {
                resultHTML += `<li><a href="${js.url}" target="_blank">${js.url}</a> - ${js.size} bytes</li>`;
            });

            resultHTML += `</ul>
                <h3>External Resources</h3>
                <ul>`;
                
            // List the external resources
            data.external_resources.forEach(external => {
                resultHTML += `<li><a href="${external.url}" target="_blank">${external.url}</a> - ${external.size} bytes</li>`;
            });

            resultHTML += `</ul>`;
            
            // Update the result container with the HTML content
            //document.getElementById('result').innerHTML = resultHTML;*/
        }
    } catch (error) {
        // Handle any unexpected errors
        document.getElementById('result').innerText = `An unexpected error occurred: ${error.message}`;
        console.error('Error:', error);
    }
});
