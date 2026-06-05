# server/worker.py
import pika
import json
import redis
import time
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Conexão com o Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def callback(ch, method, properties, body):
    dados = json.loads(body)
    task_id = dados['task_id']
    cidade = dados['cidade'].title() 
    temp = round(dados['temperatura'])

    print(f"[*] Recebido! Gerando guia Premium para {cidade}...")
    
    time.sleep(5) 

    dica = "Leve roupas leves e protetor solar!" if temp > 20 else "Leve casaco e guarda-chuva!"

    pdf = FPDF()
    pdf.add_page()
    
    # 1. MOLDURA DA PÁGINA (Contorno Azul Indigo)
    pdf.set_draw_color(79, 70, 229)
    pdf.set_line_width(1)
    pdf.rect(5, 5, 200, 287)
    
    # 2. TÍTULO DO PDF (Dividido em duas linhas centralizadas)
    pdf.set_fill_color(79, 70, 229) 
    pdf.set_text_color(255, 255, 255)
    
    # Linha 1: "Guia de Viagem" (Um pouco menor)
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 12, text="Guia de Viagem", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
    
    # Linha 2: O nome da Cidade (Bem grande e em destaque)
    pdf.set_font("helvetica", style="B", size=30)
    pdf.cell(0, 16, text=cidade, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
    
    # Adicionar a data de geração abaixo da faixa azul à direita
    data_atual = datetime.now().strftime("%d/%m/%Y as %H:%M")
    pdf.set_text_color(148, 163, 184) # Cinza claro
    pdf.set_font("helvetica", style="I", size=10)
    pdf.cell(0, 10, text=f"Gerado em {data_atual}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
    
    pdf.cell(0, 8, text="", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Espaço
    
    # 3. SECÇÃO DA TEMPERATURA 
    pdf.set_draw_color(226, 232, 240) 
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y()) # Linha superior
    
    pdf.cell(0, 5, text="", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Espaço
    
    pdf.set_text_color(100, 116, 139) 
    pdf.set_font("helvetica", style="", size=14)
    pdf.cell(0, 10, text="Temperatura Atual na cidade:", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    if temp > 25:
        pdf.set_text_color(239, 68, 68) 
    else:
        pdf.set_text_color(59, 130, 246) 

    pdf.set_font("helvetica", style="B", size=50) 
    pdf.cell(0, 25, text=f"{temp} graus", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    pdf.cell(0, 5, text="", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Espaço
    
    pdf.line(20, pdf.get_y(), 190, pdf.get_y()) # Linha inferior
    
    pdf.cell(0, 15, text="", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Espaço
    
    # 4. DICA DE VIAGEM 
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(16, 185, 129)
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 15, text=f" Dica: {dica} ", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)

    # 5. RODAPÉ DO PROJETO
    pdf.set_y(-25) 
    pdf.set_text_color(156, 163, 175)
    pdf.set_font("helvetica", style="I", size=9)
    pdf.cell(0, 10, text="Projeto de Sistemas Distribuidos - Guia de Viagem Automatico", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # SALVAR E AVISAR
    nome_arquivo = f"guia_{cidade}_{task_id[:8]}.pdf"
    pdf.output(nome_arquivo)

    dados_conclusao = {
        "status": "Concluido!",
        "completado": True,
        "arquivo": nome_arquivo
    }
    redis_client.set(f"task_{task_id}", json.dumps(dados_conclusao))
    
    print(f"[+] PDF finalizado e salvo como {nome_arquivo}")

# Conectar e escutar a fila
conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
canal = conexao.channel()
canal.queue_declare(queue='fila_pdf')

print(' [*] Worker aguardando tarefas no RabbitMQ. Pressione CTRL+C para sair.')
canal.basic_consume(queue='fila_pdf', on_message_callback=callback, auto_ack=True)
canal.start_consuming()