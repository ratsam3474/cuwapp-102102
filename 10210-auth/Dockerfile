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
EXPOSE 5502

# Start production server
CMD ["npm", "start"]
