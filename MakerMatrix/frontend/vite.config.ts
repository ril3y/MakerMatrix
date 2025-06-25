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
      watch: {
        usePolling: true,
      },
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/static': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite static paths - pass them through as-is
        },
        '/utility': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite utility paths - pass them through as-is
        },
        '/printer': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite printer paths - pass them through as-is
        },
        '/auth': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite auth paths - pass them through as-is
        },
        '/users': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite users paths - pass them through as-is
        },
        '/categories': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite categories paths - pass them through as-is
        },
        '/locations': {
          target: env.VITE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          // Don't rewrite locations paths - pass them through as-is
        },
      },
    },
  }
})