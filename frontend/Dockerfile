FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

# Catatan: proyek ini memakai CRA + CRACO dengan banyak dependency (Radix, dll).
# --legacy-peer-deps mencegah error ERESOLVE peer-dependency saat 'npm install'.
RUN npm install --legacy-peer-deps

COPY . .

RUN npm run build


FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
