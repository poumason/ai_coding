# Use a specific slim version for stability
FROM python:3.12-slim

WORKDIR /app

COPY . /app/
