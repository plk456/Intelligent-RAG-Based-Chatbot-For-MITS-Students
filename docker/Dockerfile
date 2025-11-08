# Use Node.js base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --only=production

# Copy all files
COPY .. .

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]