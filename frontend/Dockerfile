# Use a lightweight Node.js image
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json first to cache dependencies (faster builds)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of your code
COPY . .

# Expose the port Vite runs on
EXPOSE 3000

# Start the development server
# We use --host 0.0.0.0 so the container is accessible from outside
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]