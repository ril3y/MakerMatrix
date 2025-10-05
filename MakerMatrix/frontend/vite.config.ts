import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: true,
      https: {
        key: path.resolve(__dirname, '../../certs/key.pem'),
        cert: path.resolve(__dirname, '../../certs/cert.pem'),
      },
      watch: {
        usePolling: true,
      },
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'https://192.168.1.58:8443',
          changeOrigin: true,
          secure: false, // Allow self-signed certificates
          // Don't rewrite /api paths - pass them through as-is
        },
        '/static': {
          target: env.VITE_API_URL || 'https://192.168.1.58:8443',
          changeOrigin: true,
          secure: false, // Allow self-signed certificates
          // Don't rewrite static paths - pass them through as-is
        },
        '/utility': {
          target: env.VITE_API_URL || 'https://192.168.1.58:8443',
          changeOrigin: true,
          secure: false, // Allow self-signed certificates
          // Don't rewrite utility paths - pass them through as-is
        },
      },
    },
  }
})