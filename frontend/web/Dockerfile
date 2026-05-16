FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ENV HOST=0.0.0.0
ENV BROWSER=none

EXPOSE 3000
CMD ["npm", "start"]
