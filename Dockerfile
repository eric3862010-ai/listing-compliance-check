FROM python:3.12-slim
WORKDIR /app
COPY engine.py server.py http_server.py tool_schema.json rules_hktvmall.json rules_shopee_my.json sample_biotree.json ./
ENV PORT=8080 HOST=0.0.0.0
EXPOSE 8080
CMD ["python", "http_server.py"]
