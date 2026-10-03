# Stage 1: build the static site with Node.
FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite bakes this into the JavaScript at build time.
# Empty means "same origin": the browser calls the host that served the page,
# and nginx forwards /api and /uploads to the backend container.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Stage 2: serve only the built files. Node and the source code stay behind.
FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html