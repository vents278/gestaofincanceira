# Arquitetura Supabase · v0.2

## Fluxo

```text
HTML / CSS / JavaScript puro + Chart.js
         │ Fetch, token de acesso em memória
         ▼
FastAPI ────────── Supabase Auth (signup/login/user/refresh/recover/logout)
  │ identidade verificada     │ refresh em cookie HttpOnly
  ├─ SQLAlchemy + psycopg ────┴─ Supabase PostgreSQL
  │   SET LOCAL ROLE authenticated + request.jwt.claims
  │   RLS + chaves estrangeiras + transações + triggers de auditoria
  └─ JWT do próprio usuário ── Supabase Storage (bucket privado)
```

O frontend não recebe senha PostgreSQL ou chave de serviço. O FastAPI consulta `/auth/v1/user` para validar tokens; não assina JWTs próprios, não armazena hashes e não confia em IDs/papéis enviados no corpo ou em claims decodificadas sem validação. Papéis vêm de `integrantes_grupo` no banco.

Toda transação de `FinanceSession`, inclusive uma nova transação após `commit`, assume `authenticated` e configura o UUID autenticado via `set_config(..., true)`. `SET LOCAL` e a configuração local expiram ao final da transação; o pool não carrega identidade de uma requisição para outra. As queries continuam filtradas no backend e o banco aplica as políticas independentemente da API.

## Pastas e responsabilidades

| Caminho | Responsabilidade |
|---|---|
| `app/config.py` | Variáveis obrigatórias, proibição de chave service_role, PostgreSQL e TLS remoto |
| `app/auth.py` | Cliente HTTP Auth, validação remota da identidade |
| `app/dependencies.py` | Perfil, vínculo familiar e permissão administrativa |
| `app/database.py` | Engine e contexto RLS por transação |
| `app/models.py` | Mapeamento ORM do MVP, sem criar tabelas automaticamente |
| `app/schemas.py` | Entradas Pydantic, UUID e Decimal |
| `app/routers/auth.py` | Cadastro, login, refresh, callback, recuperação, senha e logout |
| `app/routers/api.py` | Contas, categorias, receitas/despesas, dashboard, convite e acerto |
| `app/routers/storage.py` | Upload limitado, metadados e download protegido |
| `app/services/finance.py` | Regras de visibilidade, vínculos, proporção e divisão |
| `app/static/` | Interface, Fetch, gráficos e temas; sem dependência de SDK Supabase |
| `supabase/migrations/` | SQL oficial versionado: DDL, relações, RLS, funções e Storage |
| `scripts/migrate.py` | Aplicação transacional ou exportação para SQL Editor, com checksums |
| `tests/` | PostgreSQL real, testes SQL adversariais, Auth/Storage HTTP simulado e navegador |

## Modelo relacional

Todos os identificadores primários são UUID, gerados com `gen_random_uuid()` ou `uuid4`. Valores monetários são `NUMERIC(15,2)` no banco, `Decimal` no Python e strings decimais no JSON.

- `usuarios.id` referencia `auth.users.id`. Nome/e-mail do perfil são inicializados da identidade do Auth; nenhuma senha fica no esquema público.
- `grupos_familiares` referencia seu criador; `integrantes_grupo` liga usuário ao grupo, papel e status. Um usuário pertence a um grupo neste MVP; a criação e entrada usam funções controladas, não inserções públicas.
- `contas_bancarias`: grupo, nome e saldo inicial.
- `categorias`: grupo, nome e tipo; combinação única.
- `receitas` e `despesas`: grupo, responsável, pagador, conta, categoria, valor, descrição, vencimento, liquidação, privacidade, cancelamento, observações e parâmetros de divisão. O modelo abstrato `Entry` compartilha campos no Python; os dados ficam em tabelas distintas.
- `cartoes_credito`: titular, conta de pagamento, limite, fechamento e vencimento.
- `faturas`: cartão, vencimento e estado.
- `parcelas`: despesa, fatura, número, valor e vencimento; parcela única por despesa/número.
- `metas_financeiras`: titular, valor-alvo, acumulado, prazo e privacidade.
- `orcamentos`: titular, categoria, mês, limite e privacidade.
- `anexos`: despesa, uploader, caminho privado, nome e tipo do arquivo.
- `auditoria`: usuário, grupo, tabela/operação, registro e data. Inserida por triggers, não editável pela aplicação. É trilha de ações; ainda não guarda versões completas before/after.
- `private.convites`: hash do código, validade e uso. Não é exposta pela Data API.
- `private.schema_migrations`: versão, checksum e data de aplicação.

Chaves estrangeiras compostas incluem `family_id` nas referências financeiras, impedindo cruzar grupos mesmo com UUID válido. Categoria inclui `kind` no vínculo para impedir usar categoria de receita numa despesa. Os índices cobrem grupo, usuário, vencimento/mês e categoria; referências frequentes de conta, despesa e cartão também são indexadas.

## Políticas de acesso

| Recurso | Consulta | Escrita |
|---|---|---|
| Perfis e integrantes | Próprio usuário e integrantes ativos do grupo | Apenas rotinas controladas de bootstrap/convite |
| Grupos | Integrantes ativos | Criação pela função autenticada |
| Contas, categorias, cartões e faturas | Integrantes ativos | Administrador do grupo |
| Receitas, despesas, metas e orçamentos | Registros visíveis do grupo; privados só pelo dono | Próprio dono ou administrador, preservando privacidade |
| Parcelas | Exige acesso à despesa vinculada | Administrador com acesso à despesa |
| Comprovantes | Exige acesso à despesa | Upload por dono/admin; objeto com prefixo do uploader |
| Auditoria | Ações do próprio ator no grupo ativo | Somente triggers no banco |

Todas as tabelas financeiras públicas têm RLS habilitado e nenhum acesso de `anon`. Receitas/despesas não têm DELETE para `authenticated`: o cancelamento é UPDATE e mantém histórico. Inserções e updates verificam tanto papel/grupo como privacidade. Funções `SECURITY DEFINER` têm `search_path` fixo e permissões limitadas. Os helpers de vínculo evitam recursão de políticas; o usuário não pode editar sua própria role. RLS não restringe o dono/superusuário: por isso o runtime sempre reduz o papel antes das consultas.

## Integridade financeira mantida

Pendências não entram no saldo. Liquidação entra uma única vez; editar recalcula e cancelar remove o impacto. Compartilhadas não são duplicadas: o acerto calcula participações e crédito do pagador sobre a mesma despesa. O percentual proporcional é uma fotografia das receitas visíveis no mês e pode ser recalculado ao editar. Centavos residuais vão para a segunda pessoa.

Saldos/indicadores respeitam privacidade, podendo diferir do extrato real. As telas mensais usam o vencimento, não fluxo de caixa por liquidação. Não há automação de parcelas, recorrências, pagamento de faturas ou transferências nesta etapa; suas regras serão testadas antes de ativar os próximos módulos.

## Etapas

1. **Atual:** infraestrutura Supabase e MVP preservado, com Auth, convites, RLS e comprovantes. Validar implantação hospedada após fornecer configuração.
2. **Gestão:** telas/regras para cartões, parcelas, faturas, recorrências, orçamento e calendário. Transferência/fatura não devem virar nova receita/despesa de consumo.
3. **Planejamento:** metas, dívidas, projeções, alertas e relatórios.
4. **Evolução:** importação, conciliação, exportação, backup/restauração e integrações.

A estrutura SQL de módulos futuros é fundação, não autorização para gerar lançamentos financeiros automaticamente. Realtime será introduzido apenas quando houver fluxo que precise de atualização entre sessões, com políticas específicas e sem expor linhas antigas privadas.
