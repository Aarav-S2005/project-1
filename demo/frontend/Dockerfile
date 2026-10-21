# Stage 1: Build production bundle
FROM node:20-alpine AS builder

WORKDIR /app

RUN npm install -g pnpm@10

COPY package.json ./
RUN pnpm install && pnpm approve-builds --all

COPY tsconfig.json tsconfig.node.json* vite.config.ts index.html ./
COPY src/ ./src/

RUN pnpm build

# Stage 2: Serve with Nginx
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 4001

CMD ["nginx", "-g", "daemon off;"]
