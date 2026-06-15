import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17202a',
        panel: '#f7f8f5',
        line: '#d8ded7',
        cobalt: '#315f72',
        signal: '#b8563c',
        moss: '#55765f'
      },
      boxShadow: {
        soft: '0 16px 50px rgba(23, 32, 42, 0.08)'
      }
    }
  },
  plugins: []
};

export default config;
