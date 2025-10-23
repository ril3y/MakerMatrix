/**
 * Server Management Helper for E2E Tests
 *
 * This module provides utilities to manage the backend server
 * during testing using the dev_manager.py script.
 */

import type { ChildProcess } from 'child_process'
import { exec, spawn } from 'child_process'
import { promisify } from 'util'
import { join } from 'path'

const execAsync = promisify(exec)

export class TestServerManager {
  private backendProcess: ChildProcess | null = null
  private frontendProcess: ChildProcess | null = null
  private readonly projectRoot: string
  private readonly backendUrl = 'http://localhost:57891'
  private readonly frontendUrl = 'http://localhost:5173'

  constructor() {
    // Assume we're running from frontend directory
    this.projectRoot = join(process.cwd(), '../..')
  }

  /**
   * Start the backend server using dev_manager.py
   */
  async startBackend(): Promise<void> {
    console.log('Starting backend server...')

    try {
      // Use venv_test Python if available
      const pythonPath = join(this.projectRoot, 'venv_test', 'bin', 'python')

      // Check if we can use the dev manager directly
      const { stdout } = await execAsync(`${pythonPath} -c "import sys; print(sys.executable)"`)
      console.log(`Using Python: ${stdout.trim()}`)

      // Start backend via uvicorn directly for better control
      this.backendProcess = spawn(
        pythonPath,
        [
          '-m',
          'uvicorn',
          'MakerMatrix.main:app',
          '--host',
          '0.0.0.0',
          '--port',
          '57891',
          '--reload',
        ],
        {
          cwd: this.projectRoot,
          stdio: 'pipe',
        }
      )

      if (this.backendProcess.stdout) {
        this.backendProcess.stdout.on('data', (data) => {
          console.log(`Backend: ${data}`)
        })
      }

      if (this.backendProcess.stderr) {
        this.backendProcess.stderr.on('data', (data) => {
          console.error(`Backend Error: ${data}`)
        })
      }

      // Wait for server to be ready
      await this.waitForServer(this.backendUrl, 30000)
      console.log('Backend server is ready')
    } catch (error) {
      console.error('Failed to start backend:', error)
      throw error
    }
  }

  /**
   * Start the frontend development server
   */
  async startFrontend(): Promise<void> {
    console.log('Starting frontend server...')

    try {
      const frontendPath = join(this.projectRoot, 'MakerMatrix', 'frontend')

      this.frontendProcess = spawn('npm', ['run', 'dev'], {
        cwd: frontendPath,
        stdio: 'pipe',
      })

      if (this.frontendProcess.stdout) {
        this.frontendProcess.stdout.on('data', (data) => {
          console.log(`Frontend: ${data}`)
        })
      }

      if (this.frontendProcess.stderr) {
        this.frontendProcess.stderr.on('data', (data) => {
          console.error(`Frontend Error: ${data}`)
        })
      }

      // Wait for server to be ready
      await this.waitForServer(this.frontendUrl, 30000)
      console.log('Frontend server is ready')
    } catch (error) {
      console.error('Failed to start frontend:', error)
      throw error
    }
  }

  /**
   * Stop the backend server
   */
  async stopBackend(): Promise<void> {
    if (this.backendProcess) {
      console.log('Stopping backend server...')
      this.backendProcess.kill('SIGTERM')

      // Wait for process to exit
      await new Promise<void>((resolve) => {
        if (this.backendProcess) {
          this.backendProcess.on('exit', () => {
            console.log('Backend server stopped')
            resolve()
          })

          // Force kill after 5 seconds
          setTimeout(() => {
            if (this.backendProcess && !this.backendProcess.killed) {
              this.backendProcess.kill('SIGKILL')
            }
            resolve()
          }, 5000)
        } else {
          resolve()
        }
      })

      this.backendProcess = null
    }
  }

  /**
   * Stop the frontend server
   */
  async stopFrontend(): Promise<void> {
    if (this.frontendProcess) {
      console.log('Stopping frontend server...')
      this.frontendProcess.kill('SIGTERM')

      // Wait for process to exit
      await new Promise<void>((resolve) => {
        if (this.frontendProcess) {
          this.frontendProcess.on('exit', () => {
            console.log('Frontend server stopped')
            resolve()
          })

          // Force kill after 5 seconds
          setTimeout(() => {
            if (this.frontendProcess && !this.frontendProcess.killed) {
              this.frontendProcess.kill('SIGKILL')
            }
            resolve()
          }, 5000)
        } else {
          resolve()
        }
      })

      this.frontendProcess = null
    }
  }

  /**
   * Stop both servers
   */
  async stopAll(): Promise<void> {
    await Promise.all([this.stopBackend(), this.stopFrontend()])
  }

  /**
   * Check if servers are running
   */
  async isBackendRunning(): Promise<boolean> {
    return this.isServerRunning(this.backendUrl)
  }

  async isFrontendRunning(): Promise<boolean> {
    return this.isServerRunning(this.frontendUrl)
  }

  /**
   * Wait for a server to be ready
   */
  private async waitForServer(url: string, timeoutMs: number = 30000): Promise<void> {
    const startTime = Date.now()

    while (Date.now() - startTime < timeoutMs) {
      try {
        const response = await fetch(url)
        if (response.status < 500) {
          return // Server is responding
        }
      } catch (_error) {
        // Server not ready yet, continue waiting
      }

      await new Promise((resolve) => setTimeout(resolve, 1000))
    }

    throw new Error(`Server at ${url} did not start within ${timeoutMs}ms`)
  }

  /**
   * Check if a server is running
   */
  private async isServerRunning(url: string): Promise<boolean> {
    try {
      const response = await fetch(url)
      return response.status < 500
    } catch {
      return false
    }
  }

  /**
   * Setup test database with clean data
   */
  async setupTestData(): Promise<void> {
    console.log('Setting up test data...')

    try {
      // Create admin user if not exists
      await fetch(`${this.backendUrl}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'admin',
          email: 'admin@test.com',
          password: 'Admin123!',
          roles: ['admin'],
        }),
      })

      // Create test parts, locations, categories, etc.
      await this.createTestEntities()

      console.log('Test data setup complete')
    } catch (error) {
      console.error('Failed to setup test data:', error)
      // Don't throw - test data setup is optional
    }
  }

  /**
   * Create test entities for consistent testing
   */
  private async createTestEntities(): Promise<void> {
    // Login to get token
    const loginResponse = await fetch(`${this.backendUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'username=admin&password=Admin123!',
    })

    if (!loginResponse.ok) {
      console.log('Admin user not found, skipping test data creation')
      return
    }

    const { access_token } = await loginResponse.json()
    const headers = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${access_token}`,
    }

    // Create test categories
    const categories = [
      { name: 'Resistors', description: 'Electronic resistors' },
      { name: 'Capacitors', description: 'Electronic capacitors' },
      { name: 'ICs', description: 'Integrated circuits' },
    ]

    for (const category of categories) {
      try {
        await fetch(`${this.backendUrl}/categories/add_category`, {
          method: 'POST',
          headers,
          body: JSON.stringify(category),
        })
      } catch (_error) {
        console.log(`Category ${category.name} may already exist`)
      }
    }

    // Create test locations
    const locations = [
      { name: 'Storage Room A', description: 'Main storage area' },
      { name: 'Workbench 1', description: 'Primary workbench' },
      { name: 'Drawer 1', description: 'Small parts drawer' },
    ]

    for (const location of locations) {
      try {
        await fetch(`${this.backendUrl}/locations/add_location`, {
          method: 'POST',
          headers,
          body: JSON.stringify(location),
        })
      } catch (_error) {
        console.log(`Location ${location.name} may already exist`)
      }
    }

    // Create test parts
    const parts = [
      {
        part_name: 'Test Resistor 10K',
        part_number: 'R001',
        description: '10K ohm resistor for testing',
        quantity: 100,
        supplier: 'LCSC',
      },
      {
        part_name: 'Test Capacitor 100nF',
        part_number: 'C001',
        description: '100nF ceramic capacitor',
        quantity: 50,
        supplier: 'DigiKey',
      },
    ]

    for (const part of parts) {
      try {
        await fetch(`${this.backendUrl}/parts/add_part`, {
          method: 'POST',
          headers,
          body: JSON.stringify(part),
        })
      } catch (_error) {
        console.log(`Part ${part.part_name} may already exist`)
      }
    }
  }

  /**
   * Clean up test data
   */
  async cleanupTestData(): Promise<void> {
    console.log('Cleaning up test data...')

    try {
      // Clear test data if needed
      // This could involve calling cleanup endpoints or resetting the database

      console.log('Test data cleanup complete')
    } catch (error) {
      console.error('Failed to cleanup test data:', error)
      // Don't throw - cleanup is optional
    }
  }
}

// Export singleton instance
export const testServerManager = new TestServerManager()
