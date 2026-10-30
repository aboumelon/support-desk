FROM node:24.18.1-slim AS build
RUN npm install --global pnpm@11.20.0
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY contracts ./contracts
COPY packages ./packages
COPY apps/web ./apps/web
RUN pnpm install --frozen-lockfile && pnpm build
FROM caddy:2.10.2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /workspace/apps/web/dist /srv
