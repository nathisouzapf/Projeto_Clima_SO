# server/worker.py
import pika
import json
import redis
import time
from fpdf import FPDF

# Conexão com o Redis (para avisar quando terminar)
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def callback(ch, method, properties, body):
    dados = json.loads(body)
    task_id = dados['task_id']
    cidade = dados['cidade'].capitalize()
    temp = dados['temperatura']

    print(f"[*] Recebido! Gerando guia para {cidade}...")
    
    # Pausa de 5 segundos para simular um processamento pesado
    time.sleep(5) 

    # Regra de negócio simples para o guia
    dica = "Leve roupas leves e protetor solar!" if temp > 20 else "Leve casaco e guarda-chuva!"

    # Geração do PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=15)
    
    # Desenhando o conteúdo no PDF
    pdf.cell(200, 10, txt=f"Guia de Viagem: {cidade}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Temperatura atual: {temp} graus", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Dica: {dica}", ln=True, align='C')
    
    # Salva o arquivo na pasta 'server'
    nome_arquivo = f"guia_{cidade}_{task_id[:8]}.pdf"
    pdf.output(nome_arquivo)

    # Avisa o Redis que acabou
    redis_client.set(f"task_{task_id}", f"Concluído! Arquivo: {nome_arquivo}")
    print(f"[+] PDF finalizado e salvo como {nome_arquivo}")

# Conecta no RabbitMQ e fica esperando mensagens na fila 'fila_pdf'
conexao = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
canal = conexao.channel()
canal.queue_declare(queue='fila_pdf')

print(' [*] Worker aguardando tarefas no RabbitMQ. Pressione CTRL+C para sair.')
canal.basic_consume(queue='fila_pdf', on_message_callback=callback, auto_ack=True)
canal.start_consuming()
