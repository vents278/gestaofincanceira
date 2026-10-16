# Rita & Jean Finance · Supabase

MVP de gestão financeira do casal: FastAPI, HTML/CSS/JavaScript puro, Chart.js, **Supabase PostgreSQL, Auth e Storage**. Não há banco SQLite nem autenticação própria em uso. A arquitetura anterior permanece no histórico do Git; arquivos locais antigos ignorados não são utilizados ou apagados.

## Preparar o Supabase

Siga o passo a passo completo em [docs/SUPABASE.md](docs/SUPABASE.md): criar projeto, configurar Auth, executar SQL, obter a conexão TLS e preparar o bucket privado. Não é necessário usar `service_role`.

```bash
bash scripts/setup.sh
cp .env.example .env
# Preencha .env em ambiente seguro; nunca envie suas credenciais ao Git.
.venv/bin/python scripts/migrate.py
bash scripts/start.sh
```

A URL/porta padrão da aplicação é `127.0.0.1:8000`, com API documentada em `/docs`. `/health` verifica o processo; `/health/ready` verifica conexão e presença da tabela fundamental. Cadastre o grupo, confirme o e-mail se exigido, entre e crie uma conta. Em **Configurações**, gere um convite para o segundo integrante: ele informa o código no próprio cadastro e cria a própria senha. Convites expiram em 48 horas, são de uso único e um novo convite invalida o anterior.

`setup.sh` instala dependências, sem acessar ou alterar o banco remoto. As migrações são uma operação explícita, com transações, trava de execução e verificação SHA-256. Para SQL Editor, use `.venv/bin/python scripts/migrate.py --sql` e cole o resultado; o histórico de migrações será o mesmo. Não edite migrações já aplicadas.

## Configuração

| Variável | Uso |
|---|---|
| `SUPABASE_URL` | Origem HTTPS do projeto |
| `SUPABASE_PUBLISHABLE_KEY` | Chave publicável ou `anon`; chaves secretas/service_role são rejeitadas |
| `DATABASE_URL` | Conexão PostgreSQL somente no servidor, com driver `postgresql+psycopg://` e TLS `verify-full` para hosts remotos |
| `APP_URL` | Origem da aplicação, também configurada nos redirects do Auth; HTTPS obrigatório fora do desenvolvimento local |
| `HOST` / `PORT` | Bind do Uvicorn; opcionais, exportados no shell |

O frontend comunica-se somente com o FastAPI. Senhas são encaminhadas ao Supabase Auth e não são persistidas pelo backend. O token de acesso fica na memória; o refresh token fica em cookie HttpOnly, SameSite Strict e Secure em HTTPS. O acesso pode ser restaurado após recarregar a página. Login, renovação, logout e recuperação são delegados ao Supabase.

Cada requisição autenticada valida o token em `/auth/v1/user`. Cada transação PostgreSQL executa `SET LOCAL ROLE authenticated` e configura a identidade verificada. Isso mantém o RLS ativo, mesmo quando a conexão administrativa tem privilégios elevados. Nunca altere esse mecanismo para executar consultas financeiras como proprietário do banco ou service_role. A disponibilidade do Auth e do banco é necessária para operações autenticadas.

## Funcionalidades do MVP preservadas

- Grupo com dois integrantes, administrador, convites e privacidade de lançamentos.
- Contas, saldo inicial, receitas e despesas previstas/liquidadas, categorias, pesquisa e filtros.
- Edição, cancelamento com confirmação, auditoria automática no PostgreSQL.
- Divisão igual, personalizada ou proporcional à renda visível do mês, com cálculo de acerto no backend.
- Dashboard, indicadores, gráficos e interface responsiva com temas claro/escuro.
- Comprovantes PDF/PNG/JPEG de até 5 MB no bucket privado. Depois de salvar uma despesa, edite-a para enviar ou baixar comprovantes.

**Interpretação financeira:** a seleção mensal usa o mês de vencimento/previsão. Previstas não alteram o saldo; somente liquidadas alteram. Saldo visível exclui registros privados do outro integrante e pode diferir do extrato. O saldo líquido previsto do mês é receita menos despesa, sem incluir o saldo inicial. A proporcionalidade usa receitas previstas/recebidas visíveis e salva o percentual; não se altera automaticamente com novas receitas. Cancelamentos preservam histórico. Para mudar receita para despesa ou vice-versa, cancele e crie outro registro. O acerto é uma obrigação calculada, sem movimentar caixa automaticamente.

O esquema inclui cartões, faturas, parcelas, metas e orçamentos, com RLS e relacionamentos. Seus módulos de negócio/telas, assim como recorrências, dívidas, projeções e exportações, continuam no roteiro original. Criar tabelas não significa que esses módulos estejam implementados. Realtime não é necessário ao fluxo atual de atualização por Fetch; a publicação de dados financeiros está desativada por segurança.

## Testar

```bash
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
node --check app/static/app.js  # opcional
```

Os testes levantam um PostgreSQL temporário real, aplicam os SQLs e exercitam RLS diretamente com papéis restritos. Auth HTTP é simulado e os esquemas `auth`/`storage` reproduzem apenas os contratos necessários. Não requerem credenciais nem alteram o Supabase hospedado. O pacote de teste `pgserver` inclui binários Linux x86_64; outras plataformas podem exigir adaptação do runner.

Para o teste de navegador, instale `requirements-browser.txt`, disponibilize Chromium e execute:

```bash
CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python tests/browser_smoke.py
```

Ele usa banco temporário e Auth simulado, percorre cadastro, convite, restauração de sessão, despesas, edição, acerto, gráficos e layout móvel. Capturas ficam em `/tmp/finance-desktop.png` e `/tmp/finance-mobile.png`.

## Documentação e limites

- [Configuração didática e implantação Supabase](docs/SUPABASE.md)
- [Arquitetura e modelo de dados](docs/ARQUITETURA.md)
- [Guia dos módulos, código e exercícios](docs/GUIA.md)
- [Especificação original e etapas futuras](docs/ESPECIFICACAO.md)

O projeto precisa das credenciais do seu Supabase para validar Auth, entrega real de e-mails, Storage e banco hospedados. Testes com contratos simulados não comprovam essa implantação. Para produção, configure SMTP, rate limits/CAPTCHA do Auth, domínio HTTPS, recuperação de senha, backup/PITR conforme seu plano e restauração testada. Há proteção por assinatura de arquivo e download forçado, mas não há antivírus de anexos. Se o upload no Storage funcionar e a gravação de metadados falhar, a aplicação tenta limpar o objeto; falhas de rede podem exigir conciliação de objetos órfãos. Não há exclusão de comprovantes na interface nesta etapa.
