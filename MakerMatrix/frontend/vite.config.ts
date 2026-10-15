import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Only enable HTTPS when the cert/key actually exist on disk. CI runners and
  // anyone without local certs (HTTPS_ENABLED=false) should fall back to HTTP.
  const keyPath = path.resolve(__dirname, '../../certs/key.pem')
  const certPath = path.resolve(__dirname, '../../certs/cert.pem')
  const httpsConfig =
    fs.existsSync(keyPath) && fs.existsSync(certPath) ? { key: keyPath, cert: certPath } : undefined

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: '0.0.0.0',
      https: httpsConfig,
      watch: {
        usePolling: true,
      },
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'https://10.2.0.2:8443',
          changeOrigin: true,
          secure: false, // Allow self-signed certificates
          // Don't rewrite /api paths - pass them through as-is
        },
      },
    },
    preview: {
      port: 4173,
      host: '0.0.0.0',
      https: httpsConfig,
    },
    build: {
      rollupOptions: {
        output: {
          // Split heavy vendor deps into long-lived cacheable chunks so the
          // initial route chunk stays small and changes to app code don't
          // bust the vendor cache.
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-motion': ['framer-motion'],
            'vendor-syntax': ['react-syntax-highlighter'],
            'vendor-charts': ['chart.js', 'react-chartjs-2'],
          },
        },
      },
    },
  }
})
