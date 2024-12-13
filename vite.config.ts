/// <reference types="vite/client" />

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ['framer-motion', 'react', 'react-dom']
  },
  server: {
    port: 8080,
    host: true,
    strictPort: true
  },
  base: "/",
  optimizeDeps: {
    include: ['framer-motion']
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'framer-motion': ['framer-motion'],
          'vendor': ['react', 'react-dom']
        }
      }
    }
  },
  preview: {
    port: 8080,
    host: true,
    strictPort: true
  }
}));