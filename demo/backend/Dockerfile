FROM node:20-alpine

WORKDIR /app

# Enable corepack and install pnpm
RUN npm install -g pnpm@10

# Copy package definition
COPY package.json ./

# Install dependencies and approve build scripts
RUN pnpm install && pnpm approve-builds --all

# Copy source code and config
COPY tsconfig.json ./
COPY src/ ./src/

# Expose microservices ports
EXPOSE 4010 4011 4012 4013

# Default environment ports
ENV USERS_PORT=4010 \
    DOCUMENTS_PORT=4011 \
    PAYROLL_PORT=4012 \
    ADMIN_PORT=4013 \
    NODE_ENV=production

CMD ["pnpm", "start"]
