# server/server.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Novo import para enviar arquivos
import os # Novo import para checar se o arquivo existe
import redis
import httpx
import pika
import json
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Conexão com o Redis (Ajustado para localhost)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# COLOQUE A SUA CHAVE DO OPENWEATHERMAP AQUI
CHAVE_CLIMA = "bf5b84a1ad77e03471167e21c1201c42"

def enviar_para_fila(mensagem):
    # Conecta no RabbitMQ (Ajustado para localhost) e manda a mensagem para a fila 'fila_pdf'
    conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    canal = conexao.channel()
    canal.queue_declare(queue='fila_pdf')
    canal.basic_publish(exchange='', routing_key='fila_pdf', body=json.dumps(mensagem))
    conexao.close()

@app.get("/clima/{cidade}")
async def gerar_guia(cidade: str):
    cidade = cidade.lower()
    
    # 1. TENTA BUSCAR NO REDIS (CACHE)
    dados_cache = redis_client.get(f"clima_{cidade}")
    if dados_cache:
        temperatura = json.loads(dados_cache)["temp"]
        fonte = "Redis (Cache)"
    else:
        # 2. SE NÃO TEM NO CACHE, BUSCA NA API REAL
        url = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={CHAVE_CLIMA}&units=metric"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Cidade não encontrada")
            temperatura = resp.json()["main"]["temp"]
            
            # Salva no Redis por 10 minutos (600 segundos)
            redis_client.setex(f"clima_{cidade}", 600, json.dumps({"temp": temperatura}))
            fonte = "OpenWeatherMap (API)"

    # 3. GERA UM ID ÚNICO PARA A TAREFA DO PDF E MANDA PRO RABBITMQ
    task_id = str(uuid.uuid4())
    mensagem_tarefa = {"task_id": task_id, "cidade": cidade, "temperatura": temperatura}
    enviar_para_fila(mensagem_tarefa)

    # Salva o status inicial da tarefa no Redis em formato JSON (Para o seu app.js ler)
    status_inicial = {"status": "Processando PDF...", "completado": False}
    redis_client.set(f"task_{task_id}", json.dumps(status_inicial))

    return {
        "cidade": cidade.capitalize(),
        "temperatura": temperatura,
        "fonte": fonte,
        "task_id": task_id
    }

# Rota para o frontend perguntar se o PDF já está pronto
@app.get("/status/{task_id}")
def checar_status(task_id: str):
    status_dados = redis_client.get(f"task_{task_id}")
    if status_dados:
        # Retorna o JSON que está salvo no Redis direto pro seu frontend
        return json.loads(status_dados)
    return {"status": "Aguardando...", "completado": False}

# NOVA ROTA: Para fazer o download do PDF
@app.get("/download/{nome_arquivo}")
def baixar_pdf(nome_arquivo: str):
    caminho_arquivo = f"./{nome_arquivo}" 
    
    if os.path.exists(caminho_arquivo):
        return FileResponse(
            path=caminho_arquivo, 
            filename=nome_arquivo, 
            media_type='application/pdf'
        )
    else:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")