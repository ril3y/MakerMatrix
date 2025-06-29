#!/usr/bin/env node

/**
 * Test script to verify MCP browser tools connection
 * This tests the browser tools server at localhost:3025
 */

const http = require('http');

// Test basic connection to browser tools server
function testBrowserToolsServer() {
    console.log('Testing browser tools server connection...');
    
    const postData = JSON.stringify({
        action: 'navigate',
        url: 'http://localhost:5173'
    });
    
    const options = {
        hostname: 'localhost',
        port: 3025,
        path: '/api/browser',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    };
    
    const req = http.request(options, (res) => {
        console.log(`Status: ${res.statusCode}`);
        console.log(`Headers: ${JSON.stringify(res.headers)}`);
        
        let data = '';
        res.on('data', (chunk) => {
            data += chunk;
        });
        
        res.on('end', () => {
            console.log('Response:', data);
            if (res.statusCode === 200) {
                console.log('✅ Browser tools server is responding');
                testMakerMatrixPage();
            } else {
                console.log('❌ Browser tools server error');
            }
        });
    });
    
    req.on('error', (e) => {
        console.error(`Request error: ${e.message}`);
        console.log('❌ Could not connect to browser tools server');
        console.log('Make sure the server is running with: npm exec @agentdeskai/browser-tools-server@1.2.1');
    });
    
    req.write(postData);
    req.end();
}

// Test accessing MakerMatrix frontend
function testMakerMatrixPage() {
    console.log('\nTesting MakerMatrix frontend access...');
    
    const options = {
        hostname: 'localhost',
        port: 5173,
        path: '/',
        method: 'GET'
    };
    
    const req = http.request(options, (res) => {
        console.log(`MakerMatrix frontend status: ${res.statusCode}`);
        
        let data = '';
        res.on('data', (chunk) => {
            data += chunk;
        });
        
        res.on('end', () => {
            if (data.includes('<title>')) {
                const title = data.match(/<title[^>]*>([^<]+)<\/title>/i);
                console.log(`✅ MakerMatrix frontend is accessible: ${title ? title[1] : 'Unknown title'}`);
            } else {
                console.log('✅ MakerMatrix frontend responding but no title found');
            }
            console.log(`Page size: ${data.length} characters`);
        });
    });
    
    req.on('error', (e) => {
        console.error(`MakerMatrix frontend error: ${e.message}`);
        console.log('❌ MakerMatrix frontend not accessible');
        console.log('Make sure frontend is running with: cd MakerMatrix/frontend && npm run dev');
    });
    
    req.end();
}

// Run tests
console.log('🧪 Testing MCP Browser Tools Setup');
console.log('=====================================');
testBrowserToolsServer();