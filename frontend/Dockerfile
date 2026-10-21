# Temporary Nginx frontend for E2E bootstrap.
# Frontend owner will replace this with a multi-stage React/Vite build.
FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
