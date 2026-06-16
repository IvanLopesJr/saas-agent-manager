# Manual de Uso — SaaS Agent Manager

## 1. Primeiros Passos

**Acessar o sistema:** abra o navegador (Chrome, Edge, Firefox) e digite o endereço fornecido pela sua equipe de TI.

**Fazer login:**
1. Digite seu **e-mail** ou **nome de usuário**
2. Digite sua **senha**
3. Marque **"Lembrar-me"** se estiver usando um computador pessoal
4. Clique em **"Entrar"**

> Se sua empresa estiver inativa ou seu usuário estiver bloqueado, o sistema não permitirá o acesso. Procure o administrador responsável.

---

## 2. Esqueci Minha Senha

1. Na tela de login, clique em **"Esqueceu a senha?"**
2. Digite seu e-mail e envie a solicitação
3. Verifique sua caixa de entrada
4. Clique no link recebido por e-mail
5. Digite a nova senha e confirme
6. Volte para a tela de login e acesse normalmente

> **Observação:** por segurança, a mensagem de confirmação pode ser genérica. Se o e-mail não estiver cadastrado, você não receberá o link.

---

## 3. Perfis de Acesso

O sistema possui dois perfis principais.

| Perfil | O que pode fazer |
|--------|------------------|
| Super Admin | Gerencia todas as empresas, usuários, agentes/chatbots, cobranças e configurações globais |
| Admin da Empresa | Gerencia dados da própria empresa, membros, agentes vinculados e cobranças da empresa |

---

## 4. Para Administradores da Empresa

O Admin da Empresa acessa apenas dados relacionados à sua própria empresa.

### 4.1. Painel Inicial

Ao fazer login, você verá um painel com informações da empresa, como:

- resumo de membros;
- agentes/chatbots vinculados;
- dados de cobrança;
- atalhos para telas importantes.

Use o menu lateral para acessar membros, cobranças, agentes e configurações.

### 4.2. Gerenciar Membros

Acesse **"Membros"** no menu.

Na tela de membros você pode:

- buscar por nome, e-mail, documento, departamento ou telefone;
- filtrar por status;
- filtrar por agente/chatbot;
- criar novo membro;
- editar cadastro;
- excluir membro;
- importar membros por CSV;
- exportar a lista de membros.

**Criar novo membro:**
1. Clique em **"Novo Membro"**
2. Preencha os dados obrigatórios
3. Informe telefone com DDI e apenas números, por exemplo: `5511999999999`
4. Se a empresa usar cobrança por agente, selecione os agentes/chatbots que o membro poderá acessar
5. Clique em **"Salvar"**

**Editar membro:** clique no ícone de lápis ao lado do membro desejado.

**Excluir membro:** clique no ícone de lixeira e confirme a exclusão.

> Membros vinculados a usuários administradores podem ser considerados na cobrança conforme a configuração da empresa.

### 4.3. Importar Membros por CSV

Acesse **"Membros"** e clique em **"Importar"**.

1. Selecione um arquivo `.csv`
2. Envie o arquivo
3. Confira a prévia da importação
4. Corrija erros bloqueantes, se houver
5. Confirme a importação

O arquivo pode conter dados como:

- nome;
- e-mail;
- telefone;
- documento;
- departamento;
- cargo;
- status;
- agentes/chatbots.

> O sistema valida o arquivo antes de importar. Registros com erro podem ser rejeitados para evitar dados inconsistentes.

### 4.4. Meus Agentes / Chatbots

Acesse **"Meus Chatbots"** no menu.

Essa tela mostra os agentes/chatbots vinculados à empresa, com informações como:

- nome;
- descrição;
- preço configurado;
- quantidade de membros com acesso.

> Se um agente não aparecer nessa tela, ele provavelmente ainda não foi vinculado à sua empresa pelo Super Admin.

### 4.5. Cobranças da Empresa

Acesse **"Cobranças"** no menu.

Você poderá visualizar as cobranças da sua empresa e usar filtros por período.

Na lista de cobranças, os principais atalhos são:

- **ícone de olho:** ver detalhes da cobrança;
- **CSV:** exportar cobrança em planilha CSV;
- **Excel:** exportar cobrança em arquivo `.xlsx`;
- **PDF:** exportar fatura em PDF.

### 4.6. Configurações da Empresa

Acesse **"Configurações"** no menu.

Você pode atualizar dados básicos da empresa, como:

- nome;
- endereço;
- telefone;
- logotipo.

> Configurações de cobrança, moeda e agentes vinculados são controladas pelo Super Admin.

---

## 5. Para Super Administradores

O Super Admin possui acesso global ao sistema.

### 5.1. Painel Geral

Ao fazer login como Super Admin, você vê indicadores gerais do ambiente, como:

- total de empresas;
- total de usuários;
- total de membros;
- total de agentes/chatbots;
- dados gerais de cobrança.

Use o menu lateral para navegar entre empresas, usuários, agentes, membros, cobranças e configurações.

### 5.2. Gerenciar Empresas

Acesse **"Empresas"** no menu.

**Criar nova empresa:**
1. Clique em **"Nova Empresa"**
2. Preencha dados cadastrais, documento fiscal e e-mail
3. Escolha a moeda
4. Escolha o modo de cobrança
5. Configure preço por membro, quando aplicável
6. Defina se administradores devem ser cobrados
7. Clique em **"Salvar"**

**Editar empresa:** clique no botão de edição na listagem ou no detalhe da empresa.

**Ativar/Inativar empresa:** acesse o detalhe da empresa e clique em **"Ativar"** ou **"Inativar"**.

> Administradores de empresa inativa não conseguem acessar o sistema.

### 5.3. Gerenciar Usuários

Acesse **"Usuários"** no menu.

Usuários são contas com acesso ao sistema. Eles podem ser Super Admin ou Admin da Empresa.

**Criar novo usuário:**
1. Clique em **"Novo Usuário"**
2. Preencha nome, e-mail, usuário e senha
3. Escolha o perfil
4. Se for Admin da Empresa, selecione a empresa
5. Defina se o usuário estará ativo
6. Clique em **"Salvar"**

**Ativar/Inativar:** clique no botão de alternância de status.

**Editar:** clique no ícone de lápis.

**Excluir:** clique no ícone de lixeira e confirme.

> O sistema não permite que você inative ou exclua seu próprio usuário pela tela de usuários.

### 5.4. Gerenciar Agentes / Chatbots

Acesse **"Chatbots"** no menu.

**Criar agente/chatbot:**
1. Clique em **"Novo Chatbot"**
2. Informe nome, descrição e preço base
3. Defina o status
4. Clique em **"Salvar"**

**Editar agente/chatbot:** clique no ícone de lápis.

**Excluir agente/chatbot:** clique no ícone de lixeira.

> Só exclua agentes que não estejam em uso. Se houver vínculo ativo com empresas, desvincule antes.

### 5.5. Vincular Agentes a Empresas

Na lista de agentes/chatbots, acesse a opção de vínculo.

Você poderá:

- selecionar empresas que terão acesso ao agente;
- definir preço customizado por empresa;
- remover vínculo de uma empresa;
- confirmar remoção quando houver membros impactados.

Ao desvincular um agente de uma empresa, os acessos ativos dos membros a esse agente são inativados.

### 5.6. Gerenciar Membros Globalmente

Acesse **"Membros"** no menu.

Como Super Admin, você pode visualizar membros de todas as empresas.

Use os filtros para buscar por:

- empresa;
- nome, e-mail, documento, departamento ou telefone;
- status;
- agente/chatbot.

Para criar um membro como Super Admin, selecione antes a empresa desejada.

### 5.7. Gerenciar Cobranças

Acesse **"Cobranças"** no menu.

Você pode:

- visualizar todas as cobranças;
- filtrar por empresa;
- filtrar por período;
- abrir detalhes;
- exportar em CSV, Excel ou PDF;
- excluir cobranças, quando necessário.

### 5.8. Gerar Cobranças

Acesse **"Cobranças"** e clique em **"Gerar Cobrança"**.

1. Informe a data inicial do período
2. Informe a data final do período
3. Selecione empresas específicas ou deixe em branco para gerar para todas as empresas ativas
4. Confirme a geração

O sistema calcula valores conforme:

- modo de cobrança da empresa;
- membros ativos no período;
- acessos ativos aos agentes no período;
- preços base e preços customizados;
- dia de corte;
- primeiro ciclo de cobrança;
- configuração de cobrança de administradores.

> Se já existir cobrança para a mesma empresa e período, o sistema informa erro e não duplica a cobrança.

### 5.9. Configurações do Sistema

Acesse **"Configurações"** no menu.

Você pode configurar:

**Identidade:**

| Campo | O que faz |
|-------|-----------|
| Nome do sistema | Nome exibido no título e nas telas |
| Logotipo | Imagem principal do sistema |
| Favicon | Ícone exibido na aba do navegador |
| Imagem de login | Imagem de fundo da tela de entrada |

**Tema visual:**

| Campo | O que faz |
|-------|-----------|
| Cores do tema | Personaliza cores principais da interface |
| Sidebar | Ajusta cores do menu lateral |
| Tipografia | Ajusta tamanhos de fonte |
| Botões | Define cores de diferentes tipos de botão |

**Cobrança:**

| Campo | O que faz |
|-------|-----------|
| Dia de corte | Ativações até esse dia são cobradas integralmente |
| Cobrar admins por padrão | Define regra inicial para novas empresas |

**SMTP:**

| Campo | O que faz |
|-------|-----------|
| Host SMTP | Servidor de envio de e-mail |
| Porta SMTP | Porta do servidor |
| Usuário SMTP | Conta usada para envio |
| Senha SMTP | Senha armazenada de forma criptografada |

> Use **"Testar Envio"** para validar a configuração SMTP.

---

## 6. Regras de Cobrança

Cada empresa pode usar um dos modos abaixo.

### 6.1. Cobrança por Usuário

Nesse modo, o sistema cobra um valor fixo por membro cobrável da empresa.

Pode considerar:

- membros ativos no período;
- administradores, se configurado;
- membros sem agente, se configurado;
- preço por membro definido na empresa.

### 6.2. Cobrança por Usuário/Agente

Nesse modo, o sistema cobra por cada acesso de membro a agente/chatbot.

Pode considerar:

- acessos ativos durante o período;
- preço base do agente;
- preço customizado do agente na empresa;
- administradores, se configurado.

### 6.3. Dia de Corte

Se a ativação ocorrer até o dia de corte, a cobrança é integral.

Se a ativação ocorrer depois do dia de corte, a cobrança é proporcional aos dias restantes do período.

### 6.4. Primeiro Ciclo

No primeiro ciclo de cobrança, o sistema usa um snapshot de preço para evitar que mudanças posteriores alterem retroativamente a primeira cobrança.

---

## 7. Importação CSV

Antes de importar membros:

- confira se a empresa correta está selecionada;
- use arquivo `.csv`;
- mantenha os cabeçalhos esperados;
- revise a prévia antes de confirmar;
- corrija erros indicados pelo sistema.

> Para grandes importações, recomenda-se testar primeiro com poucos registros.

---

## 8. Ícones e Atalhos

| Ícone | Significado |
|-------|-------------|
| Olho | Ver detalhes |
| Lápis | Editar |
| Lixeira | Excluir |
| Toggle | Ativar / Inativar |
| Download | Exportar / Baixar arquivo |
| Robô | Agente / Chatbot |
| Envelope | Testar ou enviar e-mail |
| Engrenagem | Configurações |

---

## 9. Boas Práticas

- Revise vínculos de agentes antes de gerar cobranças.
- Confira o modo de cobrança da empresa antes do primeiro faturamento.
- Use preços customizados apenas quando necessário.
- Inative empresas que não devem mais operar.
- Mantenha SMTP configurado para permitir reset de senha.
- Exporte cobranças antes de excluir registros.
- Use senhas fortes para administradores.

---

## 10. Problemas Comuns

**Não consigo fazer login.**

Verifique se usuário e senha estão corretos. Se você for Admin da Empresa, confirme com o Super Admin se sua empresa está ativa.

**Não recebi e-mail de reset de senha.**

Verifique spam/lixo eletrônico. Se não chegar, peça ao Super Admin para revisar as configurações SMTP.

**Um agente não aparece para a empresa.**

O agente precisa estar ativo e vinculado à empresa pelo Super Admin.

**Um membro não aparece na cobrança.**

Confira status do membro, período da cobrança, modo de cobrança da empresa e acessos aos agentes.

**O valor da cobrança parece diferente do esperado.**

Verifique dia de corte, data de ativação, preço customizado, cobrança de administradores e primeiro ciclo.

**Não consigo excluir uma empresa.**

Empresas com vínculos protegidos podem não ser excluídas. Nesse caso, inative a empresa em vez de excluir.
