let intervaloStatus;
const API_URL = "http://localhost:8000";

// Mapeia o botão do HTML e adiciona o evento de clique
document.getElementById('btnGerar').addEventListener('click', gerarGuia);

async function gerarGuia() {
    const cidadeInput = document.getElementById('cidade');
    const cidade = cidadeInput.value.trim();
    if (!cidade) { alert("Por favor, digite uma cidade!"); return; }

    // Reseta e exibe a área de resultados na tela
    document.getElementById('resultado').style.display = 'block';
    const statusContainer = document.getElementById('statusContainer');
    statusContainer.innerHTML = `
        <div id="statusPdf" class="status-processando">
            <span class="spinner"></span>
            <span id="statusTexto">Consultando clima e acionando fila...</span>
        </div>`;

    try {
        // 1. Faz a requisição inicial para a API REST (FastAPI)
        const res = await fetch(`${API_URL}/clima/${cidade}`);
        if (!res.ok) { throw new Error("Cidade não encontrada"); }
        
        const dados = await res.json();

        // Alimenta a tela com os dados básicos retornados
        document.getElementById('nomeCidade').innerText = dados.cidade;
        document.getElementById('temp').innerText = Math.round(dados.temperatura);
        document.getElementById('fonte').innerText = dados.fonte === 'Redis (Cache)' ? '⚡ CacheRedis' : '🌐 OpenWeatherMap';

        // 2. Inicia o Polling (perguntar ao Redis de tempos em tempos se o Worker terminou)
        clearInterval(intervaloStatus);
        intervaloStatus = setInterval(async () => {
            const resStatus = await fetch(`${API_URL}/status/${dados.task_id}`);
            const dadosStatus = await resStatus.json();
            
            document.getElementById('statusTexto').innerText = dadosStatus.status;

            // Se o Worker atualizou o status para completado, encerra o loop e mostra o download
            if (dadosStatus.completado) {
                clearInterval(intervaloStatus);
                
                statusContainer.innerHTML = `
                    <div id="statusPdf" class="status-concluido">✅ Guia gerado com sucesso!</div>
                    <a href="${API_URL}/download/${dadosStatus.arquivo}" class="btn-download" download> Baixar Guia PDF</a>
                `;
            }
        }, 1500);

    } catch (error) {
        alert(error.message === "Cidade não encontrada" ? "Cidade não encontrada! Verifique o nome." : "Erro ao conectar ao servidor.");
        document.getElementById('resultado').style.display = 'none';
    }
}