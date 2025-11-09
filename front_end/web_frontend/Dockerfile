# dùng node để build
FROM node:18-alpine AS build

WORKDIR /usr/src/app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Nginx để phục vụ build static
FROM nginx:stable-alpine
COPY --from=build /usr/src/app/dist /usr/share/nginx/html

# Nếu bạn cần cấu hình Nginx thêm cho websocket thì customize nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
