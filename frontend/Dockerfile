# ---- Frontend React (CRA/craco) -> build statis, disajikan nginx ----
FROM node:20-alpine AS build

WORKDIR /app

# REACT_APP_BACKEND_URL sengaja dikosongkan: frontend & backend satu domain,
# nginx mem-proxy /api ke service backend (lihat nginx.conf). api.js -> API = "/api".
ARG REACT_APP_BACKEND_URL=""
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV GENERATE_SOURCEMAP=false
ENV NODE_OPTIONS=--max-old-space-size=4096

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 600000

COPY . .
RUN yarn build

# ---- Tahap penyajian ----
FROM nginx:1.27-alpine

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -fsS http://localhost:80/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
