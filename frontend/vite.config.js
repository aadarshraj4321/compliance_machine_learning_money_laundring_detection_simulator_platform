import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // --- ADD THIS SECTION ---
  server: {
    host: true, // Allow external access
    port: 5173 // The port we will use
  }
})