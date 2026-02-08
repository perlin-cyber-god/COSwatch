# Use the lightweight Nginx image
FROM nginx:alpine

# 1. Clear out the default "Welcome to nginx" page
RUN rm -rf /usr/share/nginx/html/*

# 2. Copy all your files from the frontend folder into the container
COPY . /usr/share/nginx/html

# 3. CRITICAL: Rename the backup file to index.html inside the container
# This makes your space theme the default page
RUN mv /usr/share/nginx/html/index_bak.html /usr/share/nginx/html/index.html