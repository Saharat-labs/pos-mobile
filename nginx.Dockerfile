# POS-MOBILE Frontend Dockerfile (nginx)
FROM nginx:alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static files
COPY index.html /usr/share/nginx/html/
COPY script-pos.js /usr/share/nginx/html/
COPY style-pos.css /usr/share/nginx/html/
COPY manifest.json /usr/share/nginx/html/
COPY sw.js /usr/share/nginx/html/
COPY icons/ /usr/share/nginx/html/icons/
COPY LICENSE /usr/share/nginx/html/
COPY README.md /usr/share/nginx/html/
COPY USER_GUIDE.md /usr/share/nginx/html/

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]