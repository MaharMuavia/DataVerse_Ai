FROM node:20-alpine AS builder

WORKDIR /app

# Disable telemetry
ENV NEXT_TELEMETRY_DISABLED 1

# Install dependencies first for caching
COPY package*.json ./
RUN npm ci

# Copy application source
COPY . .

# Build the Next.js application
ENV NEXT_PUBLIC_API_URL http://localhost:8000/api
ENV NEXT_PUBLIC_DATAVERSE_API_URL http://localhost:8000/api
RUN npm run build

# Runner stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV production
ENV PORT 3000
ENV NEXT_TELEMETRY_DISABLED 1

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "start"]
