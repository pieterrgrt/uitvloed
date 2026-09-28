# uitvloed: de site en de server in één container.
FROM node:22-alpine
WORKDIR /app

COPY site ./site
RUN node site/bouw.mjs

COPY server/package.json server/package-lock.json ./server/
RUN cd server && npm ci --omit=dev
COPY server/src ./server/src

ENV NODE_ENV=production \
    PORT=3000 \
    UV_DATABASE=/data/uitvloed.db
RUN mkdir -p /data && chown node:node /data
VOLUME /data
EXPOSE 3000
USER node
CMD ["node", "--disable-warning=ExperimentalWarning", "server/src/start.mjs"]
