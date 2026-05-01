FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/smartchat.conf

# Copy frontend files
COPY . /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s \
    CMD wget -qO- http://localhost/ || exit 1
