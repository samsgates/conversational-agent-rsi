FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm install
FROM node:22-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web .
RUN npm run build
EXPOSE 3000
CMD ["npm","start"]
