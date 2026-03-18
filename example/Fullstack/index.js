const express = require('express');
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// EC2 API URL
const EC2_BASE_URL = 'https://ec2-18-219-58-159.us-east-2.compute.amazonaws.com';
const CREATE_VM_URL = `${EC2_BASE_URL}/api/create?developer_id=your_name&site_limit=10&delete_after=60`;

// Store for VM data (in production, use a proper data store)
const vmStore = new Map();

// Middleware
app.use(express.json());
app.use(express.static('public'));

// Health check for the EC2 API
async function checkEC2Health(vmUrl, maxRetries = 30, delayMs = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(vmUrl, { 
                method: 'HEAD',
                timeout: 5000 
            });
            if (response.status === 200) {
                return { healthy: true, url: vmUrl };
            }
            console.log(`Attempt ${i + 1}: Got status ${response.status}, retrying...`);
        } catch (error) {
            console.log(`Attempt ${i + 1}: Error - ${error.message}, retrying...`);
        }
        
        // Wait before next attempt
        if (i < maxRetries - 1) {
            await new Promise(resolve => setTimeout(resolve, delayMs));
        }
    }
    return { healthy: false, url: vmUrl };
}

// Route to create a VM and return the URL
app.get('/api/vm', async (req, res) => {
    try {
        console.log('Creating VM...');
        
        // Call the EC2 API to create a VM
        const response = await fetch(CREATE_VM_URL, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            return res.status(response.status).json({ 
                error: 'Failed to create VM', 
                details: errorText 
            });
        }
        
        const vmData = await response.json();
        console.log('VM created:', vmData);
        
        if (vmData.status !== 'success') {
            return res.status(500).json({ 
                error: 'VM creation failed', 
                details: vmData 
            });
        }
        
        const vmUrl = vmData.url;
        const containerId = vmData.container_id;
        
        // Store VM data
        vmStore.set(containerId, {
            ...vmData,
            createdAt: Date.now()
        });
        
        // Check up to 30 times if the VM URL returns 200 (not 502)
        console.log(`Checking VM health at ${vmUrl}...`);
        const healthCheck = await checkEC2Health(vmUrl);
        
        if (!healthCheck.healthy) {
            // Even if health check fails after retries, we still return the URL
            // but include a warning
            return res.json({
                ...vmData,
                warning: 'VM may still be starting up. Please refresh if you see a 502 error.',
                healthCheckAttempts: 30
            });
        }
        
        // Return the VM data with the verified URL
        return res.json({
            ...vmData,
            verified: true
        });
        
    } catch (error) {
        console.error('Error creating VM:', error);
        return res.status(500).json({ 
            error: 'Failed to create VM', 
            details: error.message 
        });
    }
});

// Dynamic route to iframe the VM - must be after /api/vm route
app.get('/api/vm/:containerId', async (req, res) => {
    const { containerId } = req.params;
    
    // Find the VM data
    const vmData = vmStore.get(containerId);
    
    if (!vmData) {
        return res.status(404).send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>VM Not Found</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                    .error { color: red; }
                </style>
            </head>
            <body>
                <h1 class="error">VM Not Found</h1>
                <p>The requested VM container ID was not found.</p>
                <p><a href="/">Go to Home</a></p>
            </body>
            </html>
        `);
    }
    
    const vmUrl = vmData.url;
    const maxSessionMinutes = vmData.max_session_minutes || 60;
    const inactivityTimeoutSeconds = vmData.inactivity_timeout_seconds || 60;
    const name = vmData.name || containerId;
    
    // Render the iframed page with countdown
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VM: ${name}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a1a;
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #2d2d2d;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #404040;
        }
        .vm-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .vm-name {
            font-size: 16px;
            font-weight: 600;
            color: #4CAF50;
        }
        .vm-id {
            font-size: 12px;
            color: #888;
            font-family: monospace;
        }
        .timer-section {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .timer {
            font-size: 18px;
            font-weight: bold;
            color: #ff9800;
            font-family: monospace;
        }
        .timer.warning {
            color: #f44336;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .inactivity-note {
            font-size: 12px;
            color: #888;
            background: #333;
            padding: 5px 10px;
            border-radius: 4px;
        }
        .vm-container {
            flex: 1;
            position: relative;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
            position: absolute;
            top: 0;
            left: 0;
        }
        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #1a1a1a;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10;
        }
        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #333;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="vm-info">
            <span class="vm-name">VM: ${name}</span>
            <span class="vm-id">ID: ${containerId.substring(0, 12)}...</span>
        </div>
        <div class="timer-section">
            <span class="inactivity-note">⚠️ Inactivity timeout: ${inactivityTimeoutSeconds}s</span>
            <span class="timer" id="timer">${maxSessionMinutes}:00</span>
        </div>
    </div>
    <div class="vm-container">
        <div class="loading-overlay" id="loading">
            <div class="loading-spinner"></div>
        </div>
        <iframe 
            id="vmFrame" 
            src="${vmUrl}" 
            allow="fullscreen; clipboard-read; clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
        ></iframe>
    </div>

    <script>
        // Session countdown
        let totalSeconds = ${maxSessionMinutes} * 60;
        const timerEl = document.getElementById('timer');
        
        function updateTimer() {
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            timerEl.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            
            // Warning when less than 5 minutes
            if (totalSeconds <= 300) {
                timerEl.classList.add('warning');
            }
            
            if (totalSeconds <= 0) {
                timerEl.textContent = 'EXPIRED';
                timerEl.classList.add('warning');
                document.getElementById('vmFrame').style.display = 'none';
                document.getElementById('loading').innerHTML = '<h2 style="color: #f44336;">Session Expired</h2>';
                return;
            }
            
            totalSeconds--;
        }
        
        // Update timer every second
        setInterval(updateTimer, 1000);
        
        // Hide loading overlay when iframe loads
        const iframe = document.getElementById('vmFrame');
        const loading = document.getElementById('loading');
        
        iframe.onload = function() {
            loading.style.display = 'none';
        };
        
        // Also handle iframe error
        iframe.onerror = function() {
            loading.innerHTML = '<h2 style="color: #f44336;">Failed to load VM</h2>';
        };
        
        // Track user activity to reset inactivity timer
        let inactivityTimer = ${inactivityTimeoutSeconds};
        
        function resetInactivityTimer() {
            inactivityTimer = ${inactivityTimeoutSeconds};
        }
        
        // Listen for user activity
        document.addEventListener('mousemove', resetInactivityTimer);
        document.addEventListener('keydown', resetInactivityTimer);
        document.addEventListener('click', resetInactivityTimer);
        document.addEventListener('scroll', resetInactivityTimer);
        
        // Check inactivity (this is just for display, actual timeout is handled by VM)
        setInterval(() => {
            inactivityTimer--;
            if (inactivityTimer <= 0) {
                // The VM will handle the actual timeout
                console.log('User inactive for ' + ${inactivityTimeoutSeconds} + ' seconds');
            }
        }, 1000);
    </script>
</body>
</html>
    `;
    
    res.setHeader('Content-Type', 'text/html');
    res.setHeader('X-Frame-Options', 'ALLOW-FROM *');
    res.send(html);
});

// Serve the client page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log(`API endpoint: http://localhost:${PORT}/api/vm`);
});
