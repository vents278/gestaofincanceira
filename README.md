# Rita & Jean Finance

Finanças pessoais e compartilhadas para duas pessoas. Primeiro incremento funcional da etapa 1 da especificação: uma aplicação FastAPI com interface em português, banco relacional e regras financeiras no servidor.

## Executar

Requisitos: Python 3.12+ e acesso ao PyPI na primeira instalação. Nenhuma credencial bancária ou conta externa é necessária.

```bash
bash scripts/setup.sh
bash scripts/start.sh
```

Abra a aplicação na porta 8000 da sua máquina. A documentação da API está em `/docs`. Crie seu grupo no primeiro acesso; não há usuários ou senhas padrão. Em **Configurações**, o administrador cadastra o segundo integrante. Em **Contas bancárias**, crie uma conta e informe o saldo inicial antes de começar os lançamentos.

`setup.sh` instala as versões fixadas em `requirements.txt` e aplica as migrações. `start.sh` usa uma chave aleatória local em `.local/jwt-secret` (ignorada pelo Git) quando `JWT_SECRET` não foi exportada. A chave é reutilizada nos reinícios. O banco local `finance.db` também não é versionado.

Para outro endereço/porta, exporte `HOST` e `PORT`. O servidor usa `127.0.0.1` por padrão. Para um banco PostgreSQL, exporte `DATABASE_URL=postgresql+psycopg://...` e execute as mesmas migrações. PostgreSQL é suportado pelo driver e pela modelagem, mas ainda não foi validado nesta entrega.

## O que funciona nesta etapa

- Cadastro, login JWT com expiração de 8 horas e hash Argon2; token mantido somente na memória do navegador.
- Grupo familiar com administrador e um segundo integrante; isolamento dos registros entre grupos.
- Cadastro de contas e saldo inicial; categorias iniciais, criação, edição e exclusão de categorias sem histórico.
- Receitas e despesas: criação, edição, pesquisa, filtros, liquidação e cancelamento com confirmação e auditoria.
- Responsável, pagador, conta, categoria, previsão/vencimento, data de liquidação, observações e privacidade por lançamento.
- Divisão igual, percentual personalizado e proporcional às receitas visíveis do mês. Acerto calculado a partir das despesas compartilhadas pagas.
- Dashboard com indicadores, gráficos Chart.js locais, filtro por mês, integrante, categoria e conta; interface responsiva e tema escuro.

Os saldos são calculados a partir do saldo inicial e dos registros liquidados, sem manter um segundo saldo mutável. Cancelar ou editar recalcula a posição, evitando débitos duplicados. Registros cancelados permanecem no banco. O acerto mostra obrigações calculadas; o registro de pagamentos de acerto é uma evolução futura.

**Privacidade e interpretação:** totais e saldos visíveis excluem os lançamentos privados do outro integrante, inclusive para administradores. Portanto, um saldo visível pode diferir do extrato real. Os gráficos e indicadores mensais usam o mês de vencimento/previsão, não o mês de caixa; “saldo líquido previsto” é receitas menos despesas cadastradas no mês, sem incorporar o saldo inicial. Os filtros aplicam-se aos lançamentos e indicadores mensais; os cards de contas exibem sempre a posição visível atual. A proporcionalidade considera receitas previstas e recebidas, salva o percentual no lançamento e só recalcula quando ele é editado.

## Verificação

```bash
.venv/bin/python -m pytest -q
node --check app/static/app.js  # opcional; Node não é necessário para executar o sistema
```

Os testes usam bancos temporários, sem tocar nos dados locais. Para o teste completo de navegador, instale `requirements-browser.txt` no ambiente virtual e disponibilize Chromium:

```bash
.venv/bin/python -m pip install -r requirements-browser.txt
CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python tests/browser_smoke.py
```

O teste abre uma instância e banco temporários na porta 8001, percorre cadastros, edição, divisão, gráficos e layout móvel; salva capturas em `/tmp/finance-desktop.png` e `/tmp/finance-mobile.png`. Não é executado pelo pytest padrão.

## Arquitetura e aprendizado

Veja [arquitetura, modelo e planejamento](docs/ARQUITETURA.md) e o [guia didático do primeiro módulo](docs/GUIA.md). O código completo de cada funcionalidade está nos arquivos indicados nesses documentos. A especificação original está em [docs/ESPECIFICACAO.md](docs/ESPECIFICACAO.md).

## Limites e próximas etapas

Esta entrega é um MVP local. Ainda não implementa cartões, parcelamentos, transferências, recorrências, metas, dívidas, orçamento, calendário, anexos, notificações, exportações e projeções avançadas. O roteiro segue as etapas da especificação; não há telas fictícias desses módulos.

Antes de uso público com dados reais: configurar HTTPS e uma chave JWT persistente no gerenciador de segredos, implantar proteção contra tentativas de login e abuso de cadastro, recuperação de senha, convites seguros, logs operacionais e rotinas de backup/restauração testadas. Desativar um usuário exige hoje uma operação administrativa no banco; não há tela de administração de status/permissões. O navegador exige novo login ao recarregar a página. A API recebe login em JSON; o Swagger requer obter o token no endpoint de login e fornecê-lo como Bearer.

Não envie bancos, arquivos `.local`, senhas ou variáveis de produção ao Git. Para um backup local consistente com SQLite, utilize a API de backup do Python `sqlite3` com destino protegido; não copie o banco enquanto estiver sendo escrito. Restauração e retenção automatizadas ficam para a etapa 4.
