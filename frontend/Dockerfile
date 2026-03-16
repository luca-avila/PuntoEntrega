# ---------- build stage ----------
FROM node:22-alpine AS build

WORKDIR /app

# Install deps with cache-friendly layering
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

# Build production bundle
RUN npm run build

# ---------- runtime stage ----------
# We don't need node at runtime if host nginx serves the static files.
# This stage is useful if you still want a container artifact.
FROM alpine:3.20 AS export

WORKDIR /out
COPY --from=build /app/dist ./dist
