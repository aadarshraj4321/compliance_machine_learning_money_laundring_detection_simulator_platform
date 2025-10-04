ARG CACHE_DATE

# --- Stage 1: Build the React application ---
# This stage is a temporary container just for building our static files.
# We use Node 18, which is a modern and stable Long-Term Support (LTS) version.
FROM node:18-alpine AS build

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker caching.
# This step only re-runs if these files change.
COPY package*.json ./

# Install all dependencies from package.json
RUN npm install

# Copy the rest of our application's source code
COPY . .

# Run the production build command. This creates an optimized 'dist' folder.
RUN npm run build

# --- Stage 2: Serve the built application with Nginx ---
# This stage creates our final, lightweight container.
FROM nginx:stable-alpine

# Copy the optimized static files from the 'build' stage into the Nginx server directory.
COPY --from=build /app/dist /usr/share/nginx/html

# Copy our custom Nginx configuration file. This is crucial for React Router to work correctly.
COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf

# Expose port 80, which is the default port Nginx listens on.
EXPOSE 80

# The default command to start the Nginx server in the foreground.
CMD ["nginx", "-g", "daemon off;"]