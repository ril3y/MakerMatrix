/**
 * Browser automation script to investigate supplier configuration frontend issues
 * This script will use the Browser Tools Server to analyze the frontend
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function investigateSupplierFrontend() {
    console.log('🔍 Starting browser investigation of supplier frontend...');
    
    let browser;
    try {
        // Launch browser through the browser tools server
        browser = await puppeteer.connect({
            browserWSEndpoint: 'ws://localhost:3025'
        });
        
        console.log('✅ Connected to browser tools server');
        
        const page = await browser.newPage();
        
        // Enable request interception to capture network calls
        await page.setRequestInterception(true);
        const failedRequests = [];
        const successfulRequests = [];
        
        page.on('request', (request) => {
            console.log(`📤 Request: ${request.method()} ${request.url()}`);
            request.continue();
        });
        
        page.on('response', (response) => {
            const status = response.status();
            const url = response.url();
            
            if (url.includes('/api/suppliers/config/suppliers')) {
                console.log(`📥 Supplier Config API Response: ${status} ${url}`);
                if (status === 404) {
                    failedRequests.push({ url, status, method: 'GET' });
                } else {
                    successfulRequests.push({ url, status, method: 'GET' });
                }
            }
        });
        
        // Capture console logs from the browser
        page.on('console', (msg) => {
            const type = msg.type();
            const text = msg.text();
            if (type === 'error' || text.includes('404') || text.includes('supplier')) {
                console.log(`🖥️ Browser Console [${type}]: ${text}`);
            }
        });
        
        // Navigate to the frontend
        console.log('🌐 Navigating to frontend at http://localhost:5173...');
        await page.goto('http://localhost:5173', { 
            waitUntil: 'networkidle2',
            timeout: 30000 
        });
        
        console.log('✅ Frontend loaded successfully');
        
        // Wait a moment for initial requests to complete
        await page.waitForTimeout(2000);
        
        // Try to navigate to supplier-related pages
        console.log('🔍 Looking for supplier configuration pages...');
        
        // Check if there are any navigation links to suppliers
        const supplierLinks = await page.evaluate(() => {
            const links = Array.from(document.querySelectorAll('a, button, [role="menuitem"]'));
            return links
                .filter(link => {
                    const text = link.textContent?.toLowerCase() || '';
                    const href = link.href || '';
                    return text.includes('supplier') || href.includes('supplier') || 
                           text.includes('config') || href.includes('config');
                })
                .map(link => ({
                    text: link.textContent?.trim(),
                    href: link.href || 'no-href',
                    className: link.className,
                    tag: link.tagName
                }));
        });
        
        console.log('🔗 Found supplier-related links:', supplierLinks);
        
        // Try to navigate to specific supplier routes if they exist
        const supplierRoutes = [
            '/suppliers',
            '/supplier-config', 
            '/configuration',
            '/settings/suppliers',
            '/admin/suppliers'
        ];
        
        for (const route of supplierRoutes) {
            try {
                console.log(`🧭 Trying route: ${route}`);
                await page.goto(`http://localhost:5173${route}`, { 
                    waitUntil: 'networkidle2',
                    timeout: 10000 
                });
                
                // Check if we're on a valid page (not 404)
                const pageTitle = await page.title();
                const url = page.url();
                
                console.log(`📄 Route ${route} loaded: ${pageTitle} (${url})`);
                
                // Wait for any API calls to complete
                await page.waitForTimeout(3000);
                
            } catch (error) {
                console.log(`❌ Route ${route} failed: ${error.message}`);
            }
        }
        
        // Check for any JavaScript errors related to missing API endpoints
        const consoleErrors = await page.evaluate(() => {
            // Return any stored console errors if the page tracks them
            return window.console._errors || [];
        });
        
        // Generate report
        const report = {
            timestamp: new Date().toISOString(),
            frontendUrl: 'http://localhost:5173',
            failedRequests: failedRequests,
            successfulRequests: successfulRequests,
            supplierLinks: supplierLinks,
            testedRoutes: supplierRoutes,
            consoleErrors: consoleErrors,
            summary: {
                missing404Calls: failedRequests.filter(r => r.url.includes('/api/suppliers/config/suppliers')),
                totalFailedRequests: failedRequests.length,
                supplierLinksFound: supplierLinks.length
            }
        };
        
        // Save report to file
        const reportPath = path.join(__dirname, 'supplier_frontend_investigation.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        
        console.log('\n📋 INVESTIGATION SUMMARY:');
        console.log('='.repeat(50));
        console.log(`✅ Frontend accessible: http://localhost:5173`);
        console.log(`❌ Failed API calls: ${failedRequests.length}`);
        console.log(`✅ Successful API calls: ${successfulRequests.length}`);
        console.log(`🔗 Supplier-related links found: ${supplierLinks.length}`);
        
        if (failedRequests.length > 0) {
            console.log('\n❌ FAILED REQUESTS:');
            failedRequests.forEach(req => {
                console.log(`   ${req.status} ${req.method} ${req.url}`);
            });
        }
        
        if (supplierLinks.length > 0) {
            console.log('\n🔗 SUPPLIER LINKS:');
            supplierLinks.forEach(link => {
                console.log(`   "${link.text}" -> ${link.href}`);
            });
        }
        
        console.log(`\n📄 Full report saved to: ${reportPath}`);
        
        // Take a screenshot for visual inspection
        const screenshotPath = path.join(__dirname, 'frontend_screenshot.png');
        await page.screenshot({ 
            path: screenshotPath,
            fullPage: true 
        });
        console.log(`📸 Screenshot saved to: ${screenshotPath}`);
        
    } catch (error) {
        console.error('❌ Investigation failed:', error);
    } finally {
        if (browser) {
            await browser.disconnect();
            console.log('🔌 Disconnected from browser');
        }
    }
}

// Run the investigation
investigateSupplierFrontend()
    .then(() => {
        console.log('✅ Investigation completed');
        process.exit(0);
    })
    .catch((error) => {
        console.error('💥 Investigation crashed:', error);
        process.exit(1);
    });