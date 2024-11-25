const API_URL = 'https://website-performance.onrender.com/get_size'; // Replace with backend URL

document.getElementById('sizeCheckerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('url').value;
    document.getElementById('result').innerText = "Checking...";
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json','Access-Control-Allow-Origin': '*','Accept': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await response.json();
        document.getElementById('result').innerText = data.error 
            ? `Error: ${data.error}` 
            : `Page size: ${data.size_mb} MB`;
    } catch (error) {
        document.getElementById('result').innerText = 'An unexpected error occurred!';
    }
});
