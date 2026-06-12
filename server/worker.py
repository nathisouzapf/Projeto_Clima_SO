import os
import pika
import json
import redis
import time
from datetime import datetime
import pytz
from fpdf import FPDF
from fpdf.enums import XPos, YPos

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# Paleta minimalista
BRANCO      = (255, 255, 255)
CREME       = (245, 240, 232)   # fundo da página
CREME_CARD  = (237, 230, 219)   # fundo dos cards
COBRE       = (201, 98, 47)     # cor principal
COBRE_CL    = (240, 210, 190)   # borda/detalhe cobre claro
TEXTO       = (30, 25, 20)      # texto principal
SUBTEXTO    = (120, 110, 95)    # texto secundário
BORDA       = (210, 200, 185)   # bordas sutis

# Cores faixas
COR_FRIO    = (59, 130, 246)
COR_AMENO   = (16, 185, 129)
COR_QUENTE  = (220, 80, 50)

def callback(ch, method, properties, body):
    dados    = json.loads(body)
    task_id  = dados['task_id']
    cidade   = dados['cidade'].title()
    temp     = round(dados['temperatura'])

    print(f"[*] Gerando guia para {cidade} ({temp}°C)...")
    time.sleep(3)

    if temp >= 28:
        faixa     = "Clima Quente"
        roupa     = "Roupas leves, claras e de tecido respiravel."
        atividade = "Praia, piscina, parques ao ar livre e passeios noturnos."
        evitar    = "Exercicios intensos ao sol entre 10h e 16h."
        cor_faixa = COR_QUENTE
    elif temp >= 18:
        faixa     = "Clima Ameno"
        roupa     = "Camiseta com uma camada leve por cima, jeans ou calca."
        atividade = "Caminhadas, turismo urbano, ciclovias e mercados locais."
        evitar    = "Sair sem uma jaqueta leve para a noite."
        cor_faixa = COR_AMENO
    else:
        faixa     = "Clima Frio"
        roupa     = "Casaco, cachecol, luvas e roupas em camadas."
        atividade = "Museus, cafes, restaurantes e passeios curtos."
        evitar    = "Ficar exposto ao vento sem protecao adequada."
        cor_faixa = COR_FRIO

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)  # ← adiciona essa linha
    W, H = 210, 297

    # ── FUNDO CREME ──────────────────────────────────────────
    pdf.set_fill_color(*CREME)
    pdf.rect(0, 0, W, H, style='F')

    # ── TOPO — linha cobre fina + marca ──────────────────────
    pdf.set_fill_color(*COBRE)
    pdf.rect(0, 0, W, 3, style='F')

    pdf.set_text_color(*COBRE)
    pdf.set_font("helvetica", style="B", size=8)
    pdf.set_xy(15, 10)
    pdf.cell(0, 5, text="* TRAVEL GUIDE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Data alinhada à direita
    data_atual = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y  %H:%M")
    pdf.set_text_color(*SUBTEXTO)
    pdf.set_font("helvetica", style="", size=8)
    pdf.set_xy(0, 10)
    pdf.cell(W - 15, 5, text=data_atual, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── NOME DA CIDADE ────────────────────────────────────────
    pdf.set_text_color(*TEXTO)
    pdf.set_font("helvetica", style="B", size=36)
    pdf.set_xy(15, 22)
    pdf.cell(0, 18, text=cidade, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Linha divisória cobre
    pdf.set_draw_color(*COBRE)
    pdf.set_line_width(0.6)
    pdf.line(15, 42, W - 15, 42)

    # ── CARD TEMPERATURA ─────────────────────────────────────
    pdf.set_fill_color(*CREME_CARD)
    pdf.set_draw_color(*BORDA)
    pdf.set_line_width(0.3)
    pdf.rect(15, 48, W - 30, 36, style='FD')

    # Label
    pdf.set_text_color(*SUBTEXTO)
    pdf.set_font("helvetica", style="", size=8)
    pdf.set_xy(22, 53)
    pdf.cell(0, 5, text="TEMPERATURA ATUAL", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Número grande
    pdf.set_text_color(*cor_faixa)
    pdf.set_font("helvetica", style="B", size=38)
    pdf.set_xy(22, 58)
    pdf.cell(70, 18, text=f"{temp}°C", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # Badge faixa
    pdf.set_fill_color(*cor_faixa)
    pdf.rect(130, 60, 60, 12, style='F')
    pdf.set_text_color(*BRANCO)
    pdf.set_font("helvetica", style="B", size=9)
    pdf.set_xy(130, 60)
    pdf.cell(60, 12, text=faixa, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── CARDS DE DICAS ────────────────────────────────────────
    def dica_card(icone, titulo, conteudo, y_start):
        # Fundo card
        pdf.set_fill_color(*CREME_CARD)
        pdf.set_draw_color(*BORDA)
        pdf.set_line_width(0.3)
        pdf.rect(15, y_start, W - 30, 34, style='FD')

        # Borda esquerda cobre
        pdf.set_fill_color(*COBRE)
        pdf.rect(15, y_start, 2.5, 34, style='F')

        # Título
        pdf.set_text_color(*SUBTEXTO)
        pdf.set_font("helvetica", style="", size=8)
        pdf.set_xy(23, y_start + 6)
        pdf.cell(0, 5, text=titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Conteúdo
        pdf.set_text_color(*TEXTO)
        pdf.set_font("helvetica", style="", size=11)
        pdf.set_xy(23, y_start + 14)
        pdf.cell(W - 42, 6, text=conteudo)

    dica_card("", "O que vestir",            roupa,     98)
    dica_card("", "Atividades recomendadas", atividade, 140)
    dica_card("", "O que evitar",            evitar,    182)

    # ── RODAPÉ ───────────────────────────────────────────────
    pdf.set_draw_color(*BORDA)
    pdf.set_line_width(0.4)
    pdf.line(15, H - 18, W - 15, H - 18)

    pdf.set_text_color(*SUBTEXTO)
    pdf.set_font("helvetica", style="", size=8)
    pdf.set_xy(0, H - 14)
    pdf.cell(W, 5, text="Projeto de Sistemas Distribuidos  *  Guia de Viagem Automatizado  *  OpenWeatherMap", align='C')

    # ── SALVAR ───────────────────────────────────────────────
    nome_arquivo = f"guia_{cidade}_{task_id[:8]}.pdf"
    os.makedirs("pdfs", exist_ok=True)
    pdf.output(f"pdfs/{nome_arquivo}")

    dados_conclusao = {"status": "Concluido!", "completado": True, "arquivo": nome_arquivo}
    redis_client.set(f"task_{task_id}", json.dumps(dados_conclusao))
    print(f"[+] PDF salvo: {nome_arquivo}")

# Conectar e escutar a fila
conexao = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
canal = conexao.channel()
canal.queue_declare(queue='fila_pdf')
print(' [*] Worker aguardando tarefas. CTRL+C para sair.')
canal.basic_consume(queue='fila_pdf', on_message_callback=callback, auto_ack=True)
canal.start_consuming()