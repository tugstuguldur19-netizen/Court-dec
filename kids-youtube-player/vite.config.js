import { defineConfig } from 'vite';

export default defineConfig({
  // Relative asset paths so the same build works on GitHub Pages
  // (served under /<repo>/) and inside the Android app.
  base: './',
  build: { target: 'es2022' },
  test: { include: ['tests/**/*.test.js'] },
});
