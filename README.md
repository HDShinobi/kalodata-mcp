# Kalodata MCP Server (TikTok Shop Analytics)

Servidor MCP (**Model Context Protocol**) construído em Python com o SDK oficial da Anthropic/MCP (`FastMCP`). Funciona como um wrapper completo para a **Kalodata Open API**, permitindo que assistentes e agentes de Inteligência Artificial (como o **Perplexity AI**, Claude, Cursor, ChatGPT e outros) realizem pesquisas aprofundadas de mercado, análise de nichos, produtos vencedores, criadores e vídeos virais do TikTok Shop.

---

## 📌 O que é este projeto?

Este servidor expõe 8 ferramentas MCP de alta performance para consulta de dados do TikTok Shop:

1. `category_rank`: Ranking de categorias de produtos ordenado por receita (faturamento).
2. `category_detail`: Detalhes completos de uma categoria de produtos.
3. `product_rank`: Ranking dos produtos mais vendidos (filtro por preço, comissão de afiliados, lojas, etc).
4. `product_detail`: Detalhes completos e métricas de um produto específico.
5. `creator_rank`: Ranking dos principais criadores/influenciadores no TikTok Shop (`/openapi/v1/crator/rank`).
6. `creator_detail`: Detalhes e métricas de desempenho de um criador (`/openapi/v1/crator/detail`).
7. `video_rank`: Ranking dos vídeos virais de vendas mais lucrativos no TikTok Shop.
8. `video_detail`: Métricas detalhadas de visualização, engajamento e receita de um vídeo.

O servidor foi projetado com suporte nativo a transporte **Streamable HTTP / SSE**, o que permite hospedá-lo remotamente e registrá-lo diretamente como um **Conector Remoto Personalizado** no Perplexity AI.

---

## 🚀 Setup Local

### 1. Pré-requisitos
- Python 3.10 ou superior instalado.
- Chave de API da Kalodata (`KALODATA_SECRET_KEY`).

### 2. Criação do Ambiente Virtual e Instalação
No terminal, dentro da pasta `kalodata-mcp`:

```bash
# Criar ambiente virtual Python
python -m venv .venv

# Ativar o ambiente virtual
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Windows (CMD):
.venv\Scripts\activate.bat
# No Linux/macOS:
source .venv/bin/activate

# Instalar as dependências
pip install -r requirements.txt
```

### 3. Configuração do Arquivo `.env`
Copie o arquivo de exemplo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` inserindo sua chave da Kalodata:
```env
KALODATA_SECRET_KEY=1c3f2274-20fb-4a01-92cf-45c9441dbe24
KALODATA_BASE_URL=https://staging.kalodata.com
PORT=8000
HOST=0.0.0.0
```
> **Nota**: Se sua chave for de ambiente de **produção**, altere a `KALODATA_BASE_URL` para o host de produção informado no e-mail de ativação da Kalodata.

---

## 🧪 Validando e Rodando Localmente

### Teste Rápido de Conexão com a API (sem MCP)
Antes de iniciar o servidor MCP, você pode validar a chave de API e a conexão com a Kalodata rodando o script de teste local:

```bash
python test_local.py
```

### Iniciar o Servidor MCP
Para iniciar o servidor HTTP Streamable localmente:

```bash
python server.py
```
O servidor será iniciado por padrão na porta `8000` (ex: `http://localhost:8000`).

### Testar com o MCP Inspector (Interface Visual de Teste)
Você pode testar e interagir visualmente com todas as ferramentas MCP usando o Inspector oficial do protocolo MCP:

```bash
npx @modelcontextprotocol/inspector python server.py
```

---

## 🌐 Deploy Remoto (Hospedagem no Render.com)

Para que o **Perplexity AI** possa se conectar ao seu servidor MCP via HTTPS remoto, você precisará hospedá-lo em uma plataforma com suporte a processos Python de longa duração. Recomendamos o **Render.com** (plano gratuito disponível):

### Passo a Passo no Render:

1. **Repositório Git**:
   - Inicialize um repositório Git na pasta do projeto e envie para o seu GitHub/GitLab:
     ```bash
     git init
     git add .
     git commit -m "Initial commit Kalodata MCP Server"
     git remote add origin https://github.com/seu-usuario/kalodata-mcp.git
     git push -u origin main
     ```

2. **Criar Web Service no Render**:
   - Acesse o painel do [Render.com](https://dashboard.render.com/) e clique em **New +** → **Web Service**.
   - Conecte o repositório do seu projeto `kalodata-mcp`.

3. **Configurações do Serviço**:
   - **Name**: `kalodata-mcp` (ou nome de sua preferência).
   - **Environment**: `Python 3`.
   - **Region**: Escolha a região mais próxima (ex: Oregon / Frankfurt).
   - **Branch**: `main`.
   - **Build Command**: `pip install -r requirements.txt`.
   - **Start Command**: `python server.py`.

4. **Variáveis de Ambiente (Environment Variables)**:
   - No painel do Render, vá em **Environment Variables** e adicione:
     - `KALODATA_SECRET_KEY`: `sua_chave_de_api_da_kalodata`
     - `KALODATA_BASE_URL`: `https://staging.kalodata.com` (ou URL de produção)
     - `PORT`: `10000` (ou deixe o Render atribuir automaticamente)

5. **Deploy**:
   - Clique em **Create Web Service**. O Render vai compilar e gerar uma URL pública HTTPS para o seu aplicativo (ex: `https://kalodata-mcp.onrender.com`).

---

## 🔗 Registrando o Conector no Perplexity AI

Após o deploy remoto ter sido concluído com sucesso e a URL pública estar ativa, siga estes passos para registrar a Kalodata no **Perplexity AI**:

1. Acesse sua conta no **Perplexity AI** (plano Pro / Enterprise).
2. Vá nas **Configurações da Conta** (Settings) → aba **Conectores** (Connectors) ou **Custom Connectors**.
3. Clique no botão **"+ Conector personalizado"** (Add Custom Connector).
4. Preencha os campos da seguinte forma:
   - **Nome do Conector**: `Kalodata TikTok Shop Analytics`
   - **Tipo de Conector**: Selecione `Remoto` (Remote).
   - **URL da Ferramenta / Servidor**: Cole a URL pública gerada no deploy (ex: `https://kalodata-mcp.onrender.com/mcp` ou `https://kalodata-mcp.onrender.com/sse`).
   - **Transporte**: Selecione `Streamable HTTP` (ou `SSE`).
   - **Tipo de Autenticação**: Selecione `Nenhuma` (None).
     > *Por que nenhuma?* Porque a autenticação com a Kalodata já é feita de forma segura no servidor Python através da variável de ambiente `KALODATA_SECRET_KEY`, sem expor nenhuma chave no Perplexity AI.
5. Clique em **Salvar / Testar Conexão**. O Perplexity irá descobrir automaticamente as 8 ferramentas expostas pelo seu servidor MCP.

---

## 🔒 Aviso de Segurança

- **NUNCA comite o arquivo `.env` com a sua chave real no Git.** O arquivo `.gitignore` já está pré-configurado para ignorar o `.env`.
- A chave de API da Kalodata fica armazenada com total segurança exclusivamente na variável de ambiente do seu servidor (localmente no `.env` e no painel do Render.com na nuvem).
