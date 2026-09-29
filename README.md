# AI Customer Service

API de atendimento ao cliente com IA, memória de conversas, classificação de intenção e transferência para atendimento humano. O projeto foi estruturado para ser executável localmente ou via Docker, com persistência PostgreSQL, migrations versionadas e documentação OpenAPI.

## Problema resolvido

Atendimentos sem contexto tendem a repetir perguntas, classificar solicitações incorretamente e perder o histórico necessário para continuidade. Esta plataforma mantém as mensagens associadas a uma conversa, fornece histórico recente e informações relevantes da base de conhecimento ao modelo, registra a intenção detectada e sinaliza quando uma pessoa deve assumir o atendimento.

## Arquitetura

```text
Cliente
	|
	v
FastAPI (rotas e validação Pydantic)
	|
	+--> Serviço de conversa --> PostgreSQL (SQLAlchemy)
	|          |                    users, conversations, messages,
	|          |                    intents, knowledge_base
	|          +--> Busca de contexto e base de conhecimento
	|          +--> API LLM compatível com OpenAI Chat Completions
	|
	+--> Swagger UI / OpenAPI
```

As rotas HTTP permanecem na raiz (`/chat`, `/conversations`, `/health`). A lógica de geração está separada do transporte HTTP e recebe o histórico e os artigos relevantes. Sem `LLM_API_KEY`, um modo local determinístico permite executar e testar o fluxo sem chamar um serviço externo. Esse modo é uma alternativa de desenvolvimento, não substitui um modelo de linguagem em produção.

## Tecnologias

- Python 3.12+
- FastAPI e Pydantic 2
- PostgreSQL 16 e SQLAlchemy 2
- Alembic para migrations
- API LLM compatível com Chat Completions
- Docker Compose
- Pytest e SQLite isolado nos testes

## Estrutura

```text
app/
	api/routes.py          Endpoints HTTP e tratamento de erros
	core/config.py         Configuração carregada do ambiente
	db/base.py             Base declarativa SQLAlchemy
	db/session.py          Engine e dependência de sessão
	main.py                Aplicação FastAPI e OpenAPI
	models.py              Users, conversations, messages, intents e knowledge_base
	schemas.py             Contratos de entrada e saída Pydantic
	services/chat.py       Contexto, persistência e orquestração do chat
	services/llm.py        Integração LLM e fallback local
migrations/              Configuração e histórico Alembic
tests/                   Testes dos endpoints e fluxos básicos
Dockerfile
docker-compose.yml
requirements.txt
```

## Instalação e execução

### Docker

```bash
cp .env.example .env
docker compose up --build
```

A API estará em `http://localhost:8000`, com documentação interativa em `http://localhost:8000/docs`. O container da API aguarda o health check do PostgreSQL e executa `alembic upgrade head` antes de iniciar o servidor.

### Execução local

Requer Python 3.12+ e PostgreSQL acessível. Crie um ambiente virtual, instale as dependências, configure o ambiente e aplique as migrations:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `DATABASE_URL` em `.env` para apontar ao PostgreSQL local. Depois:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Configuração

| Variável | Descrição | Padrão |
| --- | --- | --- |
| `DATABASE_URL` | URL SQLAlchemy do PostgreSQL | `postgresql+psycopg://postgres:postgres@localhost:5432/ai_customer_service` |
| `LLM_BASE_URL` | Endereço base da API compatível com OpenAI | `https://api.openai.com/v1` |
| `LLM_API_KEY` | Chave do provedor LLM | Vazio (ativa fallback local) |
| `LLM_MODEL` | Identificador do modelo | `gpt-4o-mini` |
| `LLM_TIMEOUT_SECONDS` | Timeout da chamada ao provedor | `30` |
| `CONVERSATION_HISTORY_LIMIT` | Número máximo de mensagens anteriores enviadas ao modelo | `20` |

Use `.env.example` como referência. O arquivo `.env` é ignorado pelo Git; não inclua chaves ou credenciais em commits. Em produção, use um gerenciador de segredos, credenciais fortes, TLS, autenticação e limites de requisição.

## API

O prefixo OpenAPI fica em `/openapi.json`; Swagger UI em `/docs` e ReDoc em `/redoc`.

| Método | Caminho | Descrição |
| --- | --- | --- |
| `POST` | `/conversations` | Cria uma conversa, opcionalmente associada a um `user_id` existente |
| `POST` | `/chat` | Envia mensagem, recupera contexto, gera e registra a resposta |
| `GET` | `/conversations/{id}` | Retorna estado e dados da conversa |
| `GET` | `/conversations/{id}/messages` | Retorna o histórico em ordem cronológica |
| `GET` | `/health` | Verifica disponibilidade da API |

### Criar conversa

```bash
curl -X POST http://localhost:8000/conversations \
	-H 'Content-Type: application/json' \
	-d '{}'
```

Resposta: objeto com `id`, `status`, `human_required` e timestamps. Guarde o `id` para enviar mensagens.

### Enviar mensagem

```bash
curl -X POST http://localhost:8000/chat \
	-H 'Content-Type: application/json' \
	-d '{"conversation_id":"<UUID_DA_CONVERSA>","message":"Preciso de ajuda com uma cobrança"}'
```

Resposta:

```json
{
	"conversation_id": "<UUID_DA_CONVERSA>",
	"message": "Entendi sua mensagem. Pode compartilhar mais detalhes para que eu possa ajudar?",
	"intent": "financeiro",
	"human_required": false,
	"escalation_reason": null
}
```

Se o cliente pedir explicitamente um atendente, a conversa é marcada com `human_required: true` e recebe um `escalation_reason`. Esse estado permanece registrado para a conversa. A mensagem do cliente e a resposta são persistidas juntas; falhas de geração não gravam uma resposta parcial.

### Consultar histórico

```bash
curl http://localhost:8000/conversations/<UUID_DA_CONVERSA>/messages
curl http://localhost:8000/conversations/<UUID_DA_CONVERSA>
curl http://localhost:8000/health
```

## Base de conhecimento e intenções

As categorias iniciais (`duvida`, `reclamacao`, `suporte`, `financeiro`, `vendas`, `cancelamento`, `outros`) são inseridas pela migration inicial. A tabela `knowledge_base` aceita perguntas, respostas, categoria e estado ativo. Entradas podem ser carregadas por uma rotina administrativa ou diretamente no banco; por exemplo:

```sql
INSERT INTO knowledge_base (id, question, answer, category, is_active)
VALUES (gen_random_uuid(), 'Qual o prazo de reembolso?', 'O reembolso é processado em até 5 dias úteis.', 'financeiro', true);
```

Não há endpoint público de administração da base nesta versão.

## Testes

```bash
python -m pytest -q
```

Os testes usam SQLite em memória e não precisam de PostgreSQL ou chave de LLM. A API real utiliza PostgreSQL e a integração LLM configurada no ambiente.

## Melhorias futuras

- Autenticação, autorização por organização e gestão de usuários.
- Endpoints administrativos auditáveis para base de conhecimento e intenções.
- Busca semântica com embeddings e recuperação de contexto mais precisa.
- Fila de atendimento humano, atribuição de agentes e resolução do escalonamento.
- Observabilidade, métricas de qualidade, rate limiting e políticas de retenção de dados.
