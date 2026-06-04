FROM python:3.10-slim

WORKDIR /app

# Copia o arquivo de requisitos para instalar as dependências
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r ./server/requirements.txt

# Copia o resto dos arquivos do projeto para dentro do container
COPY . .

EXPOSE 8000