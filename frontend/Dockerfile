# ==========================================
# STAGE 1: Build static assets using Node.js
# ==========================================
FROM node:18-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Inject relative API URL for reverse-proxy routing
ENV VITE_API_URL=/api
RUN npm run build


# ==========================================
# STAGE 2: Serve built assets using Nginx
# ==========================================
FROM nginx:1.25-alpine AS runner

# Copy customized server config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
