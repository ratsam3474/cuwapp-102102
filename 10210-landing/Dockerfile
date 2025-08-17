FROM node:18-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application
COPY . .

# Build Next.js app
RUN npm run build

# Expose port
EXPOSE 5500

# Start production server on port 5500
CMD ["npm", "run", "start", "--", "-p", "5500"]
