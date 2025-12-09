FROM node:18-alpine AS builder


# Копируем файлы зависимостей
COPY package*.json ./
COPY tsconfig.json ./

# Устанавливаем зависимости для сборки
RUN npm ci --include=dev --silent

# Копируем исходный код
COPY src/ ./src/
COPY types/ ./types/

# Собираем TypeScript
RUN npm run build

# Удаляем dev зависимости после сборки
RUN npm prune --production

FROM node:18-alpine

# Устанавливаем только необходимые пакеты
RUN apk add --no-cache curl && \
    addgroup -g 1001 -S nodejs && \
    adduser -S nodeuser -u 1001 -G nodejs


# Копируем package.json из builder
COPY --from=builder package*.json ./

# Копируем node_modules (только production)
COPY --from=builder node_modules ./node_modules

# Копируем собранный код
COPY --from=builder --chown=nodeuser:nodejs  dist ./dist

USER nodeuser

EXPOSE 8080

# Улучшенный healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Используем node для запуска
CMD ["node", "dist/client.js"]