#!/bin/sh
# Nieuwe versie van uitvloed live zetten. Draai vanuit ~/uitvloed.
set -e
git pull
docker compose up -d --build
docker image prune -f >/dev/null
docker compose ps
