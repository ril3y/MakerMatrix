/**
 * Test script to verify supplier functionality in the frontend
 * Uses browser tools server to automate testing
 */

const axios = require('axios');

async function testSupplierFrontend() {
    console.log('🔍 Testing supplier frontend functionality...');
    
    try {
        // Connect to browser tools server
        const browserToolsUrl = 'http://localhost:3025';
        
        // Create a new browser session
        console.log('📱 Creating browser session...');
        const sessionResponse = await axios.post(`${browserToolsUrl}/session`, {
            width: 1920,
            height: 1080,
            deviceScaleFactor: 1
        });
        
        const sessionId = sessionResponse.data.sessionId;
        console.log(`✅ Browser session created: ${sessionId}`);
        
        // Navigate to the frontend
        console.log('🌐 Navigating to frontend...');
        await axios.post(`${browserToolsUrl}/session/${sessionId}/navigate`, {
            url: 'http://localhost:5173'
        });
        
        // Wait for page to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Take initial screenshot
        console.log('📸 Taking initial screenshot...');
        await axios.post(`${browserToolsUrl}/session/${sessionId}/screenshot`, {
            path: 'frontend_initial.png'
        });
        
        // Try to find supplier-related navigation
        console.log('🔍 Looking for supplier navigation...');
        const navLinksResponse = await axios.post(`${browserToolsUrl}/session/${sessionId}/evaluate`, {
            expression: `
                Array.from(document.querySelectorAll('a, button, [role="menuitem"], nav *'))
                .filter(el => {
                    const text = el.textContent?.toLowerCase() || '';
                    const href = el.href || '';
                    return text.includes('supplier') || 
                           text.includes('config') || 
                           text.includes('setting') ||
                           href.includes('supplier') ||
                           href.includes('config');
                })
                .map(el => ({
                    text: el.textContent?.trim(),
                    href: el.href || 'no-href',
                    tag: el.tagName,
                    className: el.className
                }))
            `
        });
        
        console.log('🔗 Found navigation elements:', navLinksResponse.data.result);
        
        // Try to navigate to common supplier routes
        const routesToTest = [
            '/suppliers',
            '/supplier-config',
            '/configuration',
            '/settings',
            '/admin',
            '/settings/suppliers'
        ];
        
        for (const route of routesToTest) {
            try {
                console.log(`🧭 Testing route: ${route}`);
                
                await axios.post(`${browserToolsUrl}/session/${sessionId}/navigate`, {
                    url: `http://localhost:5173${route}`
                });
                
                // Wait for navigation
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Check if we're on a valid page
                const pageInfoResponse = await axios.post(`${browserToolsUrl}/session/${sessionId}/evaluate`, {
                    expression: `({
                        title: document.title,
                        url: window.location.href,
                        hasSupplierContent: document.body.innerHTML.toLowerCase().includes('supplier'),
                        hasConfigContent: document.body.innerHTML.toLowerCase().includes('config'),
                        hasAddButton: !!document.querySelector('button[class*="add"], button[title*="add"], button:contains("Add")'),
                        errorElements: Array.from(document.querySelectorAll('[class*="error"], [class*="404"]')).map(el => el.textContent)
                    })`
                });
                
                const pageInfo = pageInfoResponse.data.result;
                console.log(`📄 Route ${route} - Title: "${pageInfo.title}"`);
                console.log(`   URL: ${pageInfo.url}`);
                console.log(`   Has supplier content: ${pageInfo.hasSupplierContent}`);
                console.log(`   Has config content: ${pageInfo.hasConfigContent}`);
                console.log(`   Has add button: ${pageInfo.hasAddButton}`);
                
                if (pageInfo.errorElements && pageInfo.errorElements.length > 0) {
                    console.log(`   ⚠️ Error elements: ${pageInfo.errorElements.join(', ')}`);
                }
                
                // If this looks like a supplier page, try to interact with it
                if (pageInfo.hasSupplierContent || pageInfo.hasConfigContent) {
                    console.log(`✅ Found supplier-related page at ${route}`);
                    
                    // Take screenshot
                    await axios.post(`${browserToolsUrl}/session/${sessionId}/screenshot`, {
                        path: `supplier_page_${route.replace(/[\/]/g, '_')}.png`
                    });
                    
                    // Look for add buttons or forms
                    const interactionResponse = await axios.post(`${browserToolsUrl}/session/${sessionId}/evaluate`, {
                        expression: `
                            const addButtons = Array.from(document.querySelectorAll('button, a'))
                                .filter(el => {
                                    const text = el.textContent?.toLowerCase() || '';
                                    return text.includes('add') || text.includes('new') || text.includes('create');
                                });
                            
                            const forms = Array.from(document.querySelectorAll('form, [class*="form"]'));
                            const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
                            
                            ({
                                addButtons: addButtons.map(btn => ({
                                    text: btn.textContent?.trim(),
                                    tag: btn.tagName,
                                    className: btn.className
                                })),
                                forms: forms.length,
                                inputs: inputs.length,
                                supplierTable: !!document.querySelector('table, [class*="table"], [class*="grid"]')
                            })
                        `
                    });
                    
                    const interactions = interactionResponse.data.result;
                    console.log(`   🎯 Add buttons found: ${interactions.addButtons.length}`);
                    console.log(`   📝 Forms found: ${interactions.forms}`);
                    console.log(`   📊 Has table/grid: ${interactions.supplierTable}`);
                    
                    if (interactions.addButtons.length > 0) {
                        console.log(`   🎯 Add buttons:`, interactions.addButtons);
                        
                        // Try clicking the first add button
                        try {
                            console.log('🖱️ Attempting to click add button...');
                            await axios.post(`${browserToolsUrl}/session/${sessionId}/click`, {
                                selector: `button:contains("${interactions.addButtons[0].text}"), a:contains("${interactions.addButtons[0].text}")`
                            });
                            
                            // Wait for modal/form to appear
                            await new Promise(resolve => setTimeout(resolve, 2000));
                            
                            // Check for modal or new form
                            const modalResponse = await axios.post(`${browserToolsUrl}/session/${sessionId}/evaluate`, {
                                expression: `({
                                    modals: Array.from(document.querySelectorAll('[class*="modal"], [role="dialog"]')).length,
                                    newInputs: Array.from(document.querySelectorAll('input[placeholder*="supplier"], input[name*="supplier"]')).length,
                                    hasSupplierForm: document.body.innerHTML.toLowerCase().includes('supplier') && 
                                                   document.body.innerHTML.toLowerCase().includes('name')
                                })`
                            });
                            
                            const modalInfo = modalResponse.data.result;
                            console.log(`   📋 Modal appeared: ${modalInfo.modals > 0}`);
                            console.log(`   📝 Supplier inputs: ${modalInfo.newInputs}`);
                            console.log(`   ✅ Has supplier form: ${modalInfo.hasSupplierForm}`);
                            
                            // Take screenshot of the add form
                            await axios.post(`${browserToolsUrl}/session/${sessionId}/screenshot`, {
                                path: `supplier_add_form.png`
                            });
                            
                        } catch (clickError) {
                            console.log(`   ❌ Failed to click add button: ${clickError.message}`);
                        }
                    }
                    
                    break; // Found a working supplier page
                }
                
            } catch (routeError) {
                console.log(`❌ Route ${route} failed: ${routeError.message}`);
            }
        }
        
        // Test the API endpoints directly by monitoring network requests
        console.log('🌐 Testing API endpoint calls...');
        
        // Navigate back to main page and monitor network requests
        await axios.post(`${browserToolsUrl}/session/${sessionId}/navigate`, {
            url: 'http://localhost:5173'
        });
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Execute JavaScript to make direct API calls and check responses
        console.log('🔧 Testing supplier API endpoints...');
        const apiTestResponse = await axios.post(`${browserToolsUrl}/session/${sessionId}/evaluate`, {
            expression: `
                (async () => {
                    const results = {};
                    const baseUrl = window.location.origin.replace('5173', '8443');
                    
                    // Test the specific endpoints the frontend needs
                    const endpoints = [
                        '/api/suppliers/config/suppliers?enabled_only=false',
                        '/api/suppliers/info',
                        '/api/rate-limits/suppliers'
                    ];
                    
                    for (const endpoint of endpoints) {
                        try {
                            const response = await fetch(baseUrl + endpoint, {
                                method: 'GET',
                                headers: {
                                    'Content-Type': 'application/json'
                                }
                            });
                            
                            results[endpoint] = {
                                status: response.status,
                                statusText: response.statusText,
                                headers: Object.fromEntries(response.headers.entries())
                            };
                            
                            if (response.status === 200 || response.status === 401) {
                                try {
                                    const data = await response.text();
                                    results[endpoint].hasData = data.length > 0;
                                    results[endpoint].dataPreview = data.substring(0, 100);
                                } catch (e) {
                                    results[endpoint].dataError = e.message;
                                }
                            }
                            
                        } catch (error) {
                            results[endpoint] = {
                                error: error.message,
                                status: 'NETWORK_ERROR'
                            };
                        }
                    }
                    
                    return results;
                })()
            `
        });
        
        const apiResults = apiTestResponse.data.result;
        console.log('\n🔧 API ENDPOINT TEST RESULTS:');
        console.log('='.repeat(60));
        
        Object.entries(apiResults).forEach(([endpoint, result]) => {
            console.log(`\n📡 ${endpoint}:`);
            console.log(`   Status: ${result.status} ${result.statusText || ''}`);
            if (result.hasData) {
                console.log(`   ✅ Has data (${result.dataPreview?.length || 0} chars)`);
            }
            if (result.error) {
                console.log(`   ❌ Error: ${result.error}`);
            }
            if (result.dataPreview) {
                console.log(`   📄 Preview: ${result.dataPreview}...`);
            }
        });
        
        // Final screenshot
        await axios.post(`${browserToolsUrl}/session/${sessionId}/screenshot`, {
            path: 'frontend_final.png'
        });
        
        console.log('\n📋 TEST SUMMARY:');
        console.log('='.repeat(50));
        console.log(`✅ Browser session created: ${sessionId}`);
        console.log('📸 Screenshots saved: frontend_initial.png, supplier_*.png, frontend_final.png');
        console.log('🔧 API endpoints tested');
        
        // Check if the 404 errors are resolved
        const supplierConfigResult = apiResults['/api/suppliers/config/suppliers?enabled_only=false'];
        if (supplierConfigResult.status === 404) {
            console.log('❌ Supplier config endpoint still returning 404');
        } else if (supplierConfigResult.status === 401 || supplierConfigResult.status === 200) {
            console.log('✅ Supplier config endpoint is now working (auth required)');
        } else {
            console.log(`⚠️ Supplier config endpoint returned: ${supplierConfigResult.status}`);
        }
        
        // Clean up session
        await axios.delete(`${browserToolsUrl}/session/${sessionId}`);
        console.log('🧹 Browser session cleaned up');
        
    } catch (error) {
        console.error('💥 Test failed:', error.message);
        if (error.response) {
            console.error('Response data:', error.response.data);
        }
    }
}

// Check if axios is available, if not provide instructions
try {
    require('axios');
    testSupplierFrontend();
} catch (e) {
    console.log('❌ axios not found. Installing...');
    const { exec } = require('child_process');
    exec('npm install axios', (error, stdout, stderr) => {
        if (error) {
            console.error('Failed to install axios:', error);
            return;
        }
        console.log('✅ axios installed, running test...');
        testSupplierFrontend();
    });
}