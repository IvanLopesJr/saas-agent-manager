# SaaS Agent Manager

Sistema SaaS multiempresa para gestão de empresas, usuários administradores, membros, agentes/chatbots e cobranças recorrentes.

A aplicação permite controlar vínculos entre empresas e agentes, gerenciar membros por empresa, calcular cobranças por usuário ou por usuário/agente, exportar faturas e personalizar a identidade visual do sistema.

## Stack

- **Backend:** Django 4.2
- **Banco:** PostgreSQL 15
- **Container:** Docker + Docker Compose
- **Servidor WSGI:** Gunicorn
- **Frontend:** Django Templates + Bootstrap 5
- **Estáticos:** WhiteNoise
- **Exportações:** CSV, Excel e PDF
- **PDF:** WeasyPrint
- **Segurança SMTP:** senha armazenada com Fernet
- **Testes:** pytest + pytest-django

## Requisitos

- Docker e Docker Compose (recomendado)
- Ou Python 3.11+ e PostgreSQL 15

## Execução com Docker

```bash
cp .env.example .env
docker-compose up --build
```

Acesse:

- Aplicação: http://localhost:8000
- pgAdmin: http://localhost:5050

## Acesso Inicial

Na primeira execução, o sistema cria um Super Admin se ainda não existir nenhum usuário com esse perfil.

Configure a senha inicial no arquivo `.env`:

```env
ADMIN_PASSWORD=defina-uma-senha-forte
```

Credenciais iniciais:

- **Usuário:** `admin`
- **E-mail:** `admin@sistema.com`
- **Senha:** valor definido em `ADMIN_PASSWORD`

> Troque a senha após o primeiro acesso e nunca publique o arquivo `.env`.

## Comandos Úteis

Rodar aplicação:

```bash
docker-compose up -d
```

Parar aplicação:

```bash
docker-compose down
```

Aplicar migrations:

```bash
docker-compose exec -T web python manage.py migrate
```

Coletar arquivos estáticos:

```bash
docker-compose exec -T web python manage.py collectstatic --noinput
```

Compilar traduções:

```bash
docker-compose exec -T web python manage.py compilemessages_local
```

Rodar checagem do Django:

```bash
docker-compose exec -T web python manage.py check
```

Rodar testes:

```bash
docker-compose exec -T web pytest
```

## Estrutura do Projeto

```text
saas-agent-manager/
├── app/                         # Aplicação Django principal
│   ├── management/commands/      # Comandos customizados
│   ├── middleware/               # Auditoria e headers de segurança
│   ├── migrations/               # Migrations do banco
│   ├── static/                   # CSS, JS e imagens fonte
│   ├── templates/                # Templates Django
│   ├── tests/                    # Testes automatizados
│   ├── utils/                    # Billing, CSV, e-mail, formatadores
│   ├── views/                    # Views por domínio
│   ├── forms.py                  # Formulários
│   ├── models.py                 # Modelos de dados
│   ├── signals.py                # Signals de histórico/auditoria
│   └── urls.py                   # Rotas da aplicação
├── docs/                         # Documentação técnica complementar
├── scripts/                      # Scripts auxiliares de tradução/manutenção
├── static/                       # Arquivos estáticos globais
├── multi_empresas_chatbots/       # Configurações Django do projeto
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── MANUAL_USO.md
└── README.md
```

## Funcionalidades

- Login com usuário ou e-mail
- Redefinição de senha por e-mail
- Perfis de acesso: Super Admin e Admin da Empresa
- Cadastro e gestão de empresas
- Cadastro e gestão de usuários administradores
- Cadastro, edição, importação e exportação de membros
- Vínculo de agentes/chatbots a empresas
- Controle de acesso de membros a agentes/chatbots
- Cobrança por usuário ou por usuário/agente
- Cobrança proporcional por data de ativação
- Histórico de vigência para membros e acessos a agentes
- Geração de cobranças por período
- Exportação de cobranças em CSV, Excel e PDF
- Configurações visuais do sistema
- Configuração SMTP pela interface
- Senha SMTP criptografada
- Auditoria de ações importantes
- Interface responsiva para desktop e mobile
- Internacionalização em português, inglês e espanhol

## Regras de Cobrança

O sistema possui dois modos principais de cobrança por empresa:

| Modo | Descrição |
|------|-----------|
| Por usuário | Cobra um valor fixo por membro ativo/cobrável da empresa |
| Por usuário/agente | Cobra por cada acesso ativo de membro a agente/chatbot |

Também é possível configurar:

- cobrança ou não de administradores da empresa;
- cobrança de membros sem agente no modo por usuário;
- dia de corte para cobrança integral;
- preço customizado por agente em cada empresa;
- histórico de primeiro ciclo com snapshot de preço.

Mais detalhes estão em `docs/BILLING_LOGIC.md`.

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste os valores conforme o ambiente.

| Variável | Descrição |
|----------|-----------|
| `DB_NAME` | Nome do banco PostgreSQL |
| `DB_USER` | Usuário do banco |
| `DB_PASSWORD` | Senha do banco |
| `DB_HOST` | Host do banco |
| `DB_PORT` | Porta do banco |
| `SECRET_KEY` | Chave secreta do Django |
| `DEBUG` | Ativa/desativa modo debug |
| `ALLOWED_HOSTS` | Hosts permitidos separados por vírgula |
| `ADMIN_PASSWORD` | Senha usada para criar o Super Admin inicial |
| `EMAIL_HOST` | Servidor SMTP |
| `EMAIL_PORT` | Porta SMTP |
| `EMAIL_USE_TLS` | Ativa TLS no envio de e-mails |
| `EMAIL_HOST_USER` | Usuário SMTP |
| `EMAIL_HOST_PASSWORD` | Senha SMTP padrão do ambiente |
| `LANGUAGE_CODE` | Idioma padrão |
| `TIME_ZONE` | Fuso horário padrão |
| `SECURE_SSL_REDIRECT` | Redireciona HTTP para HTTPS |
| `SESSION_COOKIE_SECURE` | Envia cookie de sessão apenas em HTTPS |
| `CSRF_COOKIE_SECURE` | Envia cookie CSRF apenas em HTTPS |
| `SECURE_HSTS_SECONDS` | Duração do HSTS em segundos |

## Segurança

- Não publique `.env`, `media/` ou `staticfiles/`.
- Defina uma `SECRET_KEY` forte e única por ambiente.
- Use uma senha forte em `ADMIN_PASSWORD`.
- Em produção, configure `DEBUG=False`.
- Em produção com HTTPS, habilite cookies seguros e HSTS.
- O diretório `.dockerignore` evita que segredos e artefatos locais entrem no build da imagem.

## Testes

```bash
docker-compose exec -T web pytest
```

Resultado esperado:

```text
16 passed
```

## Documentação

- `MANUAL_USO.md` — manual de uso para operadores e administradores
- `docs/BILLING_LOGIC.md` — documentação da lógica de cobrança

## Publicação no GitHub

Nome recomendado do repositório:

```text
saas-agent-manager
```

Descrição sugerida:

```text
Sistema SaaS multiempresa para gestão de agentes, membros e cobranças.
```

Tópicos sugeridos:

```text
django, saas, multi-tenant, billing, postgresql, docker, bootstrap
```
