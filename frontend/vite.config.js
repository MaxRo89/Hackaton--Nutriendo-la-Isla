import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '');
  const proxy = { '/api': { target: env.API_PROXY_TARGET || 'http://127.0.0.1:5001' } };
  return {
    plugins: [react()],
    envDir: '..',
    server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
    preview: { host: '127.0.0.1', proxy },
  };
});
