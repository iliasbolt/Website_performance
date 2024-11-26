const API_URL = 'https://backend-2qtn.onrender.com/get_size'; 

document.getElementById('sizeCheckerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('url').value;
    document.getElementById('result').innerText = "Checking...";
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });
        alert(response.json());
        const data = await response.json();

        if (data.error) {
            document.getElementById('result').innerText = `Error: ${data.error}`;
        } else {
            document.getElementById('result').innerHTML = `
                <p>HTML Size: ${data.html_size_mb} MB</p>
                <p>Total Page Size: ${data.total_size_mb} MB</p>
            `;
        }
    } catch (error) {
        document.getElementById('result').innerText = 'An unexpected error occurred!'+ error;
    }
});
