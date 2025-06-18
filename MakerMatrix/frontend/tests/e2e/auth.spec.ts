import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
  });

  test('should redirect to login page when not authenticated', async ({ page }) => {
    // Should be redirected to login
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.getByText('Login to MakerMatrix')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Fill in login form
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Admin123!');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Should be redirected to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Fill in invalid credentials
    await page.fill('input[name="username"]', 'invalid');
    await page.fill('input[name="password"]', 'wrong');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.getByText(/Invalid credentials/i)).toBeVisible();
    
    // Should stay on login page
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Admin123!');
    await page.click('button[type="submit"]');
    
    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // Click logout button (might be in a dropdown or menu)
    await page.click('[data-testid="user-menu"]');
    await page.click('text=Logout');
    
    // Should be redirected to login
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should persist authentication after page reload', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Admin123!');
    await page.click('button[type="submit"]');
    
    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // Reload page
    await page.reload();
    
    // Should still be on dashboard (authentication persisted)
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('should handle session expiration', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Admin123!');
    await page.click('button[type="submit"]');
    
    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // Simulate session expiration by clearing localStorage
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // Try to navigate to a protected route
    await page.goto('/parts');
    
    // Should be redirected to login
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should prevent access to protected routes without authentication', async ({ page }) => {
    // Try to access protected routes directly
    const protectedRoutes = ['/dashboard', '/parts', '/locations', '/categories', '/suppliers'];
    
    for (const route of protectedRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/.*\/login/);
    }
  });

  test('should show loading state during authentication', async ({ page }) => {
    await page.goto('/login');
    
    // Fill in credentials
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Admin123!');
    
    // Submit form and check for loading state
    await page.click('button[type="submit"]');
    
    // Should show loading state (might be spinner or disabled button)
    await expect(page.locator('button[type="submit"]')).toBeDisabled();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept and fail the login request
    await page.route('**/auth/login', route => {
      route.abort('failed');
    });
    
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Admin123!');
    await page.click('button[type="submit"]');
    
    // Should show network error message
    await expect(page.getByText(/Network error/i)).toBeVisible();
  });

  test('should validate form fields', async ({ page }) => {
    await page.goto('/login');
    
    // Try to submit empty form
    await page.click('button[type="submit"]');
    
    // Should show validation errors
    await expect(page.getByText(/Username is required/i)).toBeVisible();
    await expect(page.getByText(/Password is required/i)).toBeVisible();
    
    // Fill only username
    await page.fill('input[name="username"]', 'admin');
    await page.click('button[type="submit"]');
    
    // Should still show password validation error
    await expect(page.getByText(/Password is required/i)).toBeVisible();
  });
});