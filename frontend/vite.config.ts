import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve, dirname } from 'path'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  base: './',
  appType: 'spa',
  root: '.',
  publicDir: 'src/public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/util': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/read': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/assets': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
    configureServer(server) {
      console.log('[Vite] configureServer called')
      server.middlewares.use((req, res, next) => {
        const url = req.url || ''
        console.log('[Vite Middleware] Received:', req.method, url)
        // Skip API, static assets, and Vite internals
        if (url.startsWith('/@') || url.startsWith('/api') || url.startsWith('/util') ||
            url.startsWith('/read') || url.startsWith('/assets') || url.startsWith('/static') ||
            url.includes('.')) {
          return next()
        }
        // Serve index.html for SPA routes
        console.log('[Vite Middleware] Serving index.html for:', url)
        const indexPath = resolve(__dirname, 'index.html')
        try {
          const content = readFileSync(indexPath, 'utf-8')
          res.setHeader('Content-Type', 'text/html')
          res.statusCode = 200
          res.end(content)
        } catch {
          console.log('[Vite Middleware] Error serving index.html')
          next()
        }
      })
    },
  },
})
