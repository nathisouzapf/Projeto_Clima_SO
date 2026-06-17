# O import do FastAPI é para instanciar a aplicação web e gerenciar as rotas HTTP.
# O HTTPException é uma estratégia para tratamento de erros, ele avisa o navegador do usuário quando algo da errado
from fastapi import FastAPI, HTTPException
# Permite que o Frontend web converse com o Backend sem ser bloqueado pelo navegador
from fastapi.middleware.cors import CORSMiddleware 
# Transmite o arquivo até o navegador do usuário quando clica em "Baixar PDF"
from fastapi.responses import FileResponse 
# Utilizado para checar se o PDF existe no disco rígido
import os 
# Permite enviar comandos para o banco de dados em memória Redis
import redis 
# Faz a requisição para buscar os dados na API
import httpx 
# Importa a biblioteca do sistema de filas
import pika 
# Transforma os dados para que o Front e o Back se conversem
import json
# Gera strings aleatórias para dar um ID para cada PDF 
import uuid 

# O FastAPI foi escolhido por ser assíncrono, 
# ele consegue atender vários usuários ao mesmo tempo sem travar, gastando pouca memória RAM
app = FastAPI() 

# Ativa a permissão do CORS para liberar que qualquer site ou frontend acesse a API sem ser bloqueada
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Conectei o Redis usando o nome 'host=redis' porque o Docker Compose cria um sistema de redes
# interno, onde os containers se acham pelo nome do serviço.
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# O os.getenv foi utilizado para ler a chave da API a partir do arquivo oculto .env
chave_clima = os.getenv("OPENWEATHER_API_KEY", "bf5b84a1ad77e03471167e21c1201c42")

# A função enviar para a fila anota a solicitação do usuário e envia para a fila do RabbitMQ
# A responsabilidade de criar o PDF ficou para o Worker pois é um processo lento e pesado que poderia travar a aplicação
def enviar_para_fila(mensagem):
    # Conecta no RabbitMQ e manda a mensagem para a fila 'fila_pdf'
    conexao = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq')) #Abre a conexão com o servidor local do RabbitMQ
    canal = conexao.channel() #Cria um canal dentro da conexão para trafegar os comandos de envio de dados
    # o queue_declare() garante que a fila exista antes do envio
    canal.queue_declare(queue='fila_pdf')
    canal.basic_publish(exchange='', routing_key='fila_pdf', body=json.dumps(mensagem)) #Diz para qual fila a mensagem deve ir
    conexao.close() #Fecha a conexão com o RabbitMQ

# Utilizei async para definir que a rota é assíncrona, se várias pessoas fizerem solicitações ao mesmo tempo,
# O servidor vai processar todas juntas, alternando as tarefas
@app.get("/clima/{cidade}") #Criação da rota tipo GET - Captura a solicitação do usuário e manda para a função
async def gerar_guia(cidade: str): #Define a função da rota de forma assíncrona
    cidade = cidade.lower() #Transforma o nome da cidade solicitada em letras minúsculas para não duplicar o cache 
    
    #TENTA BUSCAR NO REDIS (CACHE)
    # Utilizei o Redis para guardar os dados na memória rápida, pois consultar a API a cada requisição seria muito lento
    dados_cache = redis_client.get(f"clima_{cidade}")
    if dados_cache: #Se retornou algo na busca é convertido de volta em dicionário, extraindo o valor do campo "temp" e informa que o dado veio direto do Redis
        temperatura = json.loads(dados_cache)["temp"]
        fonte = "Redis (Cache)"
    else:
        #SE NÃO TEM NO CACHE, BUSCA NA API REAL
        url = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={chave_clima}&units=metric"
        async with httpx.AsyncClient() as client: #Abre um cliente HTTP assíncrono para fazer a requisição para a internet
            # Utilizei o await para informar que esse processo pode demorar um pouco 
            # Para o servidor ir atendendo outros usuários enquanto aguarda
            resp = await client.get(url) #Faz a chamada GET para a URL da API externa
            if resp.status_code != 200: #Verifica se o servidar resppondeu algo diferente de SUCESSO(200)
                raise HTTPException(status_code=404, detail="Cidade não encontrada") #Se der erro, interrompe a execução e devolve 404
            temperatura = resp.json()["main"]["temp"] #Se deu sucesso, transforma em JSON para capturar a temperatura real
            
            # O setex com 600 segundos define que após 10 minutos o Redis vai apagar esse dado de sua memória rápida
            # Próxima requisição o dado será buscado da API
            # Escolhi 10 minutos por ser um intervalo de tempo em que a temperatura da região não sofre grandes alterações
            redis_client.setex(f"clima_{cidade}", 600, json.dumps({"temp": temperatura}))
            fonte = "OpenWeatherMap (API)" #Informa que a fonte foi a API

    #GERA UM ID ÚNICO PARA A TAREFA DO PDF E MANDA PRO RABBITMQ
    task_id = str(uuid.uuid4())
    mensagem_tarefa = {"task_id": task_id, "cidade": cidade, "temperatura": temperatura} #Dicionário com dados necessários para o Worker construir o documento
    enviar_para_fila(mensagem_tarefa) #Joga os dados dentro do RabbitMQ

    #Salva o status inicial da tarefa no Redis em formato JSON 
    status_inicial = {"status": "Processando PDF...", "completado": False}
    redis_client.set(f"task_{task_id}", json.dumps(status_inicial))

    #Encerra a rota respondendo ao usuário as informações do clima
    return {
        "cidade": cidade.capitalize(),
        "temperatura": temperatura,
        "fonte": fonte,
        "task_id": task_id
    }

# Criei uma rota de Polling para que o Frontend consulte o Redis de tempo em tempo para descobrir se o status mudou para concluído
@app.get("/status/{task_id}")
def checar_status(task_id: str):
    status_dados = redis_client.get(f"task_{task_id}") #Vai até o Redis e busca o valor da chave da tarefa
    if status_dados:
        # Retorna o JSON que está salvo no Redis direto pro frontend
        return json.loads(status_dados)
    return {"status": "Aguardando...", "completado": False}

# Rota para fazer o download do PDF
@app.get("/download/{nome_arquivo}") #Cria a rota final onde o botão de download irá apontar
def baixar_pdf(nome_arquivo: str):
    caminho_arquivo = f"pdfs/{nome_arquivo}" #Mostra o caminho onde o arquivo deve estar gravado na pasta do projeto
    
    if os.path.exists(caminho_arquivo): #Checa se existe o arquivo PDF no disco rígido
        return FileResponse(     #Retorna o download do PDF 
            path=caminho_arquivo, 
            filename=nome_arquivo, 
            media_type='application/pdf'
        )
    else: #Se o arquivo não foi encontrado dispara um erro 404
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")