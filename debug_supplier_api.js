// Copy and paste this into your browser console to test the API directly
async function testSupplierAPI() {
    console.log('🧪 Testing /api/suppliers/configured endpoint...');
    
    const token = localStorage.getItem('auth_token');
    console.log('Auth token exists:', !!token);
    
    try {
        const response = await fetch('/api/suppliers/configured', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        console.log('Status:', response.status);
        console.log('Status Text:', response.statusText);
        console.log('Headers:', Object.fromEntries(response.headers.entries()));
        
        const text = await response.text();
        console.log('Raw response (first 500 chars):', text.substring(0, 500));
        
        if (text.startsWith('<!doctype') || text.startsWith('<html')) {
            console.log('❌ Got HTML instead of JSON - this means the API route is not found');
            console.log('The backend is serving the frontend HTML instead of hitting the API endpoint');
        } else {
            try {
                const json = JSON.parse(text);
                console.log('✅ Valid JSON response:', json);
            } catch (e) {
                console.log('❌ Invalid JSON:', e.message);
            }
        }
    } catch (error) {
        console.log('❌ Request failed:', error);
    }
}

// Run the test
testSupplierAPI();