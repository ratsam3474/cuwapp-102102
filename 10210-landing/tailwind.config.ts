import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#1a4d2e',     // Dark green
          secondary: '#0f3d0f',   // Darker green
          accent: '#2d5f3f',      // Medium dark green
          black: '#000000',       // Black
          light: '#f8f9fa',       // Light grey
        }
      },
      container: {
        padding: '1rem', 
        center: true,
      },
      keyframes: {
        'infinite-scroll': {
          from: { transform: 'translateX(0)' },
          to: { transform: 'translateX(-100%)' },
        },  
        gradient: {
          to: {
            backgroundPosition: "var(--bg-size) 0",
          },
        },
      },
      animation: {
        'infinite-scroll': 'infinite-scroll 25s linear infinite',
        gradient: "gradient 8s linear infinite",
       
      },
      
    },
  },
  
  plugins: [require("tailwindcss-animate")],
};
export default config;
