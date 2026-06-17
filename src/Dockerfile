# Utilizei o FROM para definir qual é a imagem base 'python:3.13', 
# pois é a versão Python da minha máquina física
# Utilizei a variante 'slim' (Debian sem pacotes extras ), 
# pois é a mais indicada por reduzir o tamanho da imagem e o tempo de build
FROM python:3.13-slim

# Utilizei o WORKDIR para criar e definir o diretório '/app', onde todos os comandos seguintes serão executado.
WORKDIR /app

# Utilizei o COPY para copiar o 'requirements.txt' antes do código-fonte
# O Docker trabalha com cache por camadas. Se o 'requirements.txt' não for alterado, o cache das dependências será reaproveitado
COPY requirements.txt .

# Utilizei o RUN para executar o pip e instalar as bibliotecas que estão no 'requirements.txt'
# Utilizei o '--no-cache-dir' para que o pip não guarde os arquivos de download temporários dentro do container
# Isso garante que na camada final tenha somente os pacotes necessários para execução
RUN pip install --no-cache-dir -r requirements.txt

# Utilizei o COPY novamente para copiar o restante do projeto para dentro do container
# Deixei ela para o final pois se eu alterar o código fonte, 
# ele não vai precisar instalar novamente as dependências, que são mais pesadas
COPY . .

# Utilizei o EXPOSE para documentar que a aplicação está configurada para responder na porta 8000
# Porém, quem publica a porta 8000 para o host acessar é o 'docker-compose.yml'
EXPOSE 8000

# Utilizei o CMD para definir o comando que será executado quando o container iniciar
# "uvicorn" é um servidor web utilizado para processar as requisições HTTP da API
# "server:app" instrui o Uvicorn a abrir o arquivo server.py e rodar a aplicação que está na variável 'app' (FastAPI())
# "--host" informa ao Uvicorn que o próximo item do array será o endereço IP que o servidor irá usar para escutar as conexões que chegam.
# "0.0.0.0" permite que o Uvicorn receba conexões vindas de qualquer lugar 
# "--port" informa ao Uvicorn que o próximo item do array será a porta que a aplicação vai atender
# "8000" define que o canal de comunicação da API é a porta 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]