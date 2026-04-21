# ---------- build stage ----------
FROM node:22-alpine AS build

WORKDIR /app

# Install deps with cache-friendly layering
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

ARG VITE_API_BASE_URL=/api
ARG VITE_GOOGLE_MAPS_API_KEY=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_GOOGLE_MAPS_API_KEY=${VITE_GOOGLE_MAPS_API_KEY}

# Build production bundle
RUN npm run build

# ---------- runtime stage ----------
# We don't need node at runtime if host nginx serves the static files.
# This stage is useful if you still want a container artifact.
FROM alpine:3.20 AS export

WORKDIR /out
COPY --from=build /app/dist ./dist
