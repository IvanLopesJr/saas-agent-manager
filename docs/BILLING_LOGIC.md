# Lógica de Cobrança – Sistema Multi-Empresas

Este documento descreve, em nível de implementação, como o sistema calcula cobranças no modo **por usuário** (`per_user`) e **por usuário/chatbot** (`per_user_chatbot`). O objetivo é permitir que qualquer desenvolvedor consiga rastrear tabelas, campos e funções envolvidos sem ambiguidades.

---

## 1. Modelos e Campos Relevantes

| Modelo / Tabela | Campos chave | Observação |
| --------------- | ------------ | ---------- |
| `Company` (`app/models.py`) | `billing_mode`, `member_price`, `bill_admin_users`, `currency`, `currency_symbol` | Define como a empresa será cobrada e o preço base. |
| `CompanyMember` | `status`, `user`, `first_cycle_price_snapshot`, `first_cycle_completed`, timestamps | Representa cada membro. Quando `user` está preenchido, o membro está vinculado a um usuário administrador da empresa. Os campos de snapshot garantem que só o primeiro ciclo seja proporcional. |
| `MemberChatbotAccess` | `activation_date`, `status`, `first_cycle_price_snapshot`, `first_cycle_completed` | Controla o acesso de um membro a um chatbot específico (apenas no modo per_user_chatbot). |
| `CompanyChatbot` | `custom_price`, `chatbot`, `company` | Permite customizar o preço de um chatbot por empresa. Usado ao calcular os snapshots. |
| `Billing` | `period_start`, `period_end`, `total_value`, `company` | Cabeçalho da cobrança mensal. |
| `BillingDetail` | `member`, `user`, `chatbot`, `billing_type`, `unit_price`, `value`, `days_active` | Cada item cobrado. `unit_price` armazena o valor base efetivamente usado naquele ciclo. |
| `SystemSettings` | `billing_cutoff_day`, `default_bill_admin_users`, SMTP, branding etc. | O dia de corte (`billing_cutoff_day`) determina se uma ativação gera cobrança integral ou proporcional. |

### Onde cada valor fica armazenado
- **Preço do primeiro ciclo por membro**: `CompanyMember.first_cycle_price_snapshot`.
- **Preço do primeiro ciclo por chatbot**: `MemberChatbotAccess.first_cycle_price_snapshot`.
- **Preço utilizado numa cobrança específica**: `BillingDetail.unit_price`.
- **Status do primeiro ciclo**: `first_cycle_completed` em `CompanyMember` e `MemberChatbotAccess`.
- **Logs e auditoria**: ver `AuditLog`, mas não participam diretamente dos cálculos.

---

## 2. Fluxo de Cálculo

### 2.1 Geração principal (`app/utils/billing.py`)
1. **Entrada**: `generate_billing_for_company(company, period_start, period_end, generated_by)`.
2. Busca `SystemSettings` para obter `billing_cutoff_day`.
3. Calcula `total_days` do período.
4. Delegação:
   - `_calculate_per_user_billing(...)` se `company.billing_mode == 'per_user'`.
   - `_calculate_per_chatbot_billing(...)` caso contrário.
5. Cria `Billing` e insere cada item de `BillingDetail` dentro de uma transação.

### 2.2 `_calculate_per_user_billing`
Fluxo detalhado:
1. Obtém membros ativos (`CompanyMember.objects.filter(status='active')`).
2. Para cada membro:
   - Busca o primeiro `MemberChatbotAccess` ativo para obter `activation_date`. Mesmo no modo per_user usamos os acessos para saber quando o membro entrou no ecossistema de chatbots.
   - Determina se está no **primeiro ciclo**:
     ```python
     is_first_cycle = (
         earliest_access
         and not member.first_cycle_completed
         and period_start <= earliest_access.activation_date <= period_end
     )
     ```
   - Define o preço:
     ```python
     price_snapshot = member.first_cycle_price_snapshot or company.member_price
     member_price = price_snapshot if is_first_cycle else company.member_price
     ```
   - Aplica o dia de corte (`billing_cutoff_day`):
     - `activation_date.day <= cutoff`: cobrança integral (`value = member_price`).
     - Caso contrário: proporcional (`daily_rate = member_price / total_days` e `value = daily_rate * dias_restantes`).
   - Armazena em `BillingDetail` (com `unit_price = member_price`).
   - Se for primeiro ciclo, adiciona o `member.id` a um set para marcar `first_cycle_completed=True` após a persistência.
3. Admins (`Company.bill_admin_users`):
   - Admins não são cobrados diretamente a partir de `User`.
   - Um admin só entra na cobrança se existir como `CompanyMember` ativo.
   - Quando `Company.bill_admin_users == False`, membros vinculados a usuários admin (`CompanyMember.user IS NOT NULL`) são excluídos do cálculo.
   - Quando `Company.bill_admin_users == True`, esses membros permanecem no cálculo normal de membros ativos.
4. Ao final, executa:
   ```python
   CompanyMember.objects.filter(id__in=members_first_cycle_to_close).update(first_cycle_completed=True)
   ```

### 2.3 `_calculate_per_chatbot_billing`
Utiliza os acessos diretamente:
1. Seleciona `MemberChatbotAccess` ativos no período (`status='active'` e `activation_date <= period_end`).
2. Para cada acesso:
   - Acha o `CompanyChatbot` correspondente para obter o preço customizado (`company_chatbot.get_price()`).
   - Calcula `is_first_cycle` baseado em `access.first_cycle_completed`.
   - Define o `effective_price` usando o snapshot do acesso.
   - Aplica regra de cutoff igual ao modo per_user.
   - Cria `BillingDetail` com `member`, `chatbot`, `unit_price`.
   - Se era o primeiro ciclo, inclui o `access.id` em `access_ids_to_close`.
3. Admins (`Company.bill_admin_users`):
   - Admins não geram custo fixo separado.
   - Um admin só é cobrado se existir como `CompanyMember` ativo e possuir `MemberChatbotAccess` ativo.
   - Quando `Company.bill_admin_users == False`, acessos de membros vinculados a usuários admin (`member.user IS NOT NULL`) são excluídos.
   - Quando `Company.bill_admin_users == True`, esses acessos entram no cálculo normalmente, usando o preço do chatbot correspondente.
4. Atualiza os acessos que completaram o primeiro ciclo:
   ```python
   MemberChatbotAccess.objects.filter(id__in=access_ids_to_close).update(first_cycle_completed=True)
   ```

### 2.4 `calculate_estimated_cost(company, include_admins=None)`
- Utilizado nos dashboards para exibir "custo mensal estimado".
- Para `per_user`: conta membros ativos com acessos ativos e multiplica por `member_price`. Membros vinculados a admins só entram quando `include_admins=True` ou `Company.bill_admin_users=True`.
- Para `per_user_chatbot`: soma o preço de cada `MemberChatbotAccess` ativo (`company_chatbot.get_price()`). Acessos de membros vinculados a admins só entram quando `include_admins=True` ou `Company.bill_admin_users=True`.

---

## 3. Persistência e Rastreamento

- **Snapshots**:
  - `CompanyMember.first_cycle_price_snapshot` armazena o `member_price` vigente ao ativar o membro. É preenchido no `save()` do `CompanyMember`.
  - `MemberChatbotAccess.first_cycle_price_snapshot` armazena o preço do `CompanyChatbot` no momento do vínculo.
- **Detalhes da cobrança**:
  - `BillingDetail.unit_price` mantém o valor utilizado em cada item.
  - `BillingDetail.billing_type` indica se foi "Integral" ou "Proporcional".
  - `BillingDetail.value` representa o valor efetivo (após prorrateio, se existente).
- **Migrações**:
  - Os campos de snapshot devem existir tanto em `CompanyMember` quanto em `MemberChatbotAccess`. As migrações `0008` e `0010` cuidam disso; remova/ajuste migrações intermediárias que os excluam (ex.: 0004/0009) para evitar inconsistências.

---

## 4. Cenários de Negócio

### Primeiro ciclo proporcional
- Apenas o período em que o membro/acesso é ativado após o `billing_cutoff_day` recebe desconto proporcional.
- Depois que `first_cycle_completed=True`, meses seguintes cobram sempre o valor integral, mesmo se a ativação original tivesse sido após o cutoff.

### Reativação
- Quando um membro sai de `inactive/pending` para `active`, o `save()` reseta:
  ```python
  self.first_cycle_price_snapshot = company.member_price
  self.first_cycle_completed = False
  ```
- Para os acessos (`MemberChatbotAccess`), o fluxo é análogo.

### Alteração de preço
- Se `Company.member_price` ou `CompanyChatbot.custom_price` for alterado, os snapshots existentes não mudam (preservam o histórico). Novas ativações usam o preço atualizado.
- `BillingDetail.unit_price` sempre reflete o valor usado naquele mês, facilitando auditoria mesmo após ajustes de preço.

### Admins
- Controlados por `Company.bill_admin_users`, mas sempre a partir do vínculo com `CompanyMember`.
- `User` administrador, sozinho, não gera cobrança.
- Para ser cobrado, o admin precisa existir como `CompanyMember` ativo.
- No modo `per_user`, o admin vinculado é cobrado como qualquer outro membro ativo com acesso a chatbot.
- No modo `per_user_chatbot`, o admin vinculado é cobrado pelos `MemberChatbotAccess` ativos que possuir.
- Quando `Company.bill_admin_users=False`, membros/acessos vinculados a admins são ignorados no cálculo e no custo estimado.

---

## 5. Fluxo de Operação (Visão Geral)

1. **Cadastro/edição de membros**:
   - Feito via `member_create` / `member_edit` (`app/views/members.py`).
   - O formulário `CompanyMemberForm` salva o membro e permite selecionar chatbots.
2. **Vínculos de chatbots**:
   - Cada seleção no formulário cria/ativa `MemberChatbotAccess` (ajusta snapshots automaticamente).
3. **Geração de cobrança**:
   - Tela `/billing/generate/` (`billing_generate`) ou comando `python manage.py generate_monthly_billing`.
   - A view/command chama `generate_billing_for_company` para cada empresa/período.
4. **Persistência**:
   - `Billing` guarda o total.
   - `BillingDetail` guarda cada item, com `unit_price`, `billing_type`, `value`.
   - Após gerar, `first_cycle_completed` é atualizado para membros/acessos relevantes.
5. **Dashboards/Relatórios**:
   - O dashboard (`app/views/dashboard.py`) usa `calculate_estimated_cost` e dados agregados de `Billing`/`BillingDetail`.
   - As telas de detalhe cobram `detail_per_user.html`/`detail_per_chatbot.html`, que exibem preço base, tipo de cobrança e valor.
   - Exportações CSV/Excel (`billing_export_csv` / `billing_export_excel`) também incluem `unit_price`.

---

## 6. Arquivos e Pontos de Extensão

- **Cálculos**: `app/utils/billing.py`.
- **Persistência**: modelos em `app/models.py`, migrações em `app/migrations/`.
- **Entradas de usuário**: `app/views/members.py`, `app/forms.py`.
- **Geração e exportação**: `app/views/billing.py`, templates em `app/templates/billing/`.
- **Configurações globais**: `app/views/system_settings.py` (usa `SystemSettingsForm` para editar `billing_cutoff_day`, SMTP etc.).
- **Relatórios/Dashboards**: `app/views/dashboard.py`, `app/templates/dashboard/`.

---

Com este documento, cada regra de negócio (proporcional vs integral, snapshots, cobrança de admins) está mapeada para os campos e funções que a implementam. Qualquer alteração futura deve considerar os pontos listados acima para manter a consistência do sistema de faturamento.***
---

## 7. Visão passo a passo (perspectiva do usuário)

1. **Login e acesso**  
   - O usuário (admin ou super admin) acessa `/login/`. Após autenticação, super admins vão para o dashboard global (`dashboard_super_admin`); admins, para o dashboard da própria empresa (`dashboard_admin_empresa`).
2. **Cadastro/edição de membros**  
   - Pelo menu "Membros" (`member_list`) o usuário cria ou edita registros (`member_create`, `member_edit`).  
   - Ao salvar um membro ativo, o backend captura `member_price` (ou preço atual do chatbot) e grava em `first_cycle_price_snapshot`, reiniciando o ciclo proporcional quando necessário.
3. **Vinculação de chatbots e preços**  
   - Super admins cadastram chatbots e vinculam a empresas (`chatbots/vincular.html`), ajustando `custom_price` em `CompanyChatbot`.  
   - Admins selecionam quais chatbots cada membro acessa; isso cria/ativa `MemberChatbotAccess` com snapshots de preço.
4. **Configuração de cobrança**  
   - O super admin define o dia de corte e regras globais em "Configurações do Sistema".  
   - O admin da empresa pode alterar dados da própria empresa (logos, telefones) e ver como os preços impactam o custo estimado.
5. **Geração de cobrança**  
   - Via tela "Gerar Cobrança" (`billing_generate`), o usuário escolhe o período e as empresas. O sistema chama `generate_billing_for_company`, calcula `Billing`/`BillingDetail` e registra auditoria.
6. **Consulta e exportação**  
   - Em "Cobranças" (`billing_list`), o usuário abre cada fatura (`billing_detail`) para ver os itens com `unit_price`, tipo (Integral/Proporcional) e valor final.  
   - Botões de exportação (`billing_export_csv`, `billing_export_excel`) geram arquivos com as mesmas informações.
7. **Dashboards e métricas**  
   - Os dashboards exibem cards e gráficos alimentados pelos dados acima (nº de membros ativos, custo estimado, top empresas, evolução de faturamento).
8. **Auditoria**  
   - Eventos críticos (geração de cobrança, mudança de preço, login) são registrados em `AuditLog`, permitindo rastreabilidade para admins.
9. **Repetição mensal**  
   - No fim de cada período, repete-se o processo: cadastrar mudanças, vincular chatbots e gerar a cobrança para que os snapshots e detalhes reflitam a situação mais recente.

Esse passo a passo resume a experiência completa: o usuário mantém membros/chatbots atualizados, define preços, gera as cobranças e consulta relatórios/exportações – enquanto o sistema aplica automaticamente as regras de dia de corte, snapshots e faturamento proporcional.


