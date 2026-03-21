const express = require('express');
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// EC2 API URL
const EC2_BASE_URL = 'https://ec2-18-219-58-159.us-east-2.compute.amazonaws.com';
const EC2_HOST = 'ec2-18-219-58-159.us-east-2.compute.amazonaws.com';
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
        
        // Get optional premium code from query parameter
        const premiumCode = req.query.premium || '';
        
        // Build the API URL with optional premium code
        let apiUrl = CREATE_VM_URL;
        if (premiumCode) {
            apiUrl += `&premium=${encodeURIComponent(premiumCode)}`;
        }
        
        // Call the EC2 API to create a VM
        const response = await fetch(apiUrl, {
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

// Route to connect to an existing port (Friend's VM)
app.get('/api/connect/:port', async (req, res) => {
    const { port } = req.params;
    const vmUrl = `http://${EC2_HOST}:${port}/`;
    
    try {
        console.log(`Manually connecting to port ${port}...`);
        
        // Use a generic container ID for manual connections
        const containerId = `manual-${port}`;
        
        // Check health of the manual port
        console.log(`Checking health for manual port ${port} at ${vmUrl}...`);
        const healthCheck = await checkEC2Health(vmUrl);
        
        const vmData = {
            status: 'success',
            url: vmUrl,
            container_id: containerId,
            port: port,
            name: `Friend's Session (${port})`,
            verified: healthCheck.healthy
        };
        
        // Store in vmStore so the dynamic iframe route can find it
        vmStore.set(containerId, {
            ...vmData,
            createdAt: Date.now(),
            max_session_minutes: 60, // Default for manual
            inactivity_timeout_seconds: 60 // Default for manual
        });
        
        return res.json(vmData);
        
    } catch (error) {
        console.error('Error connecting to port:', error);
        return res.status(500).json({ 
            error: 'Failed to connect to port', 
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
    <title>VM Console | ${name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0a0a0d;
            --header-bg: #12121a;
            --primary-color: #ff6b00;
            --text-main: #e1e1e6;
            --text-muted: #9494a3;
            --border-color: rgba(255, 107, 0, 0.15);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-color);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .header {
            background: var(--header-bg);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            z-index: 20;
        }

        .vm-brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-small {
            width: 24px;
            height: 24px;
            background: var(--primary-color);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #000;
            font-weight: 800;
            font-size: 14px;
        }

        .vm-name {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
        }

        .vm-id-tag {
            font-size: 11px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.03);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
        }

        .controls {
            display: flex;
            align-items: center;
            gap: 24px;
        }

        .timer-box {
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: monospace;
            font-weight: 700;
            color: var(--primary-color);
            font-size: 16px;
        }

        .timer-box.warning {
            color: #ff5252;
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .inactivity-status {
            font-size: 12px;
            color: var(--text-muted);
        }

        .vm-viewport {
            flex: 1;
            position: relative;
            background: #000;
        }

        iframe {
            width: 100%;
            height: 100%;
            border: none;
            position: absolute;
            top: 0; left: 0;
        }

        .overlay {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: var(--bg-color);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 10;
            gap: 20px;
        }

        .loader {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255, 107, 0, 0.1);
            border-top: 3px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <div class="vm-brand">
            <div class="logo-small">U</div>
            <span class="vm-name">${name}</span>
            <span class="vm-id-tag">${containerId.substring(0, 12)}</span>
        </div>
        <div class="controls">
            <span class="inactivity-status">⚠️ Inactivity Protocol Active (${inactivityTimeoutSeconds}s)</span>
            <div class="timer-box" id="timer">${maxSessionMinutes}:00</div>
        </div>
    </div>
    <div class="vm-viewport">
        <div class="overlay" id="loading">
            <div class="loader"></div>
            <p style="font-size: 13px; color: var(--text-muted);">Attaching to workspace...</p>
        </div>
        <iframe 
            id="vmFrame" 
            src="${vmUrl}" 
            allow="fullscreen; clipboard-read; clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
        ></iframe>
    </div>

    <script>
        let totalSeconds = ${maxSessionMinutes} * 60;
        const timerEl = document.getElementById('timer');
        
        const updateTimer = () => {
            const m = Math.floor(totalSeconds / 60);
            const s = totalSeconds % 60;
            timerEl.textContent = m + ':' + (s < 10 ? '0' : '') + s;
            
            if (totalSeconds <= 300) timerEl.classList.add('warning');
            
            if (totalSeconds <= 0) {
                timerEl.textContent = 'EXPIRED';
                document.getElementById('vmFrame').style.display = 'none';
                document.getElementById('loading').style.display = 'flex';
                document.getElementById('loading').innerHTML = '<h2 style="color: #ff5252;">Session Expired</h2>';
                return;
            }
            totalSeconds--;
        };
        
        setInterval(updateTimer, 1000);
        
        const iframe = document.getElementById('vmFrame');
        const loading = document.getElementById('loading');
        
        iframe.onload = () => loading.style.display = 'none';
        iframe.onerror = () => {
            loading.innerHTML = '<h2 style="color: #ff5252;">Failed to load environment</h2>';
        };
    </script>
</body>
</html>
    `;
    
    res.setHeader('Content-Type', 'text/html');
    res.setHeader('X-Frame-Options', 'SAMEORIGIN');
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
