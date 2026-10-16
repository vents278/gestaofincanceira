# Arquitetura e planejamento

## Visão completa

O navegador serve HTML e CSS e usa JavaScript/Fetch para chamar uma API na mesma origem. A API autentica o JWT, valida o corpo com Pydantic, verifica permissões e executa regras de negócio com `Decimal`. O SQLAlchemy persiste os registros em SQLite no desenvolvimento; Alembic versiona o esquema. A mesma estrutura está preparada para PostgreSQL por `DATABASE_URL`.

```text
Navegador (HTML/CSS/JS + Chart.js)
        │ JSON + Authorization: Bearer
        ▼
FastAPI → autenticação → rotas → serviços financeiros
                                   │ transação SQLAlchemy
                                   ▼
                             SQLite / PostgreSQL
```

### Pastas

```text
app/
  main.py             aplicação, página, arquivos estáticos e headers de segurança
  database.py         engine, sessões e ativação de foreign keys SQLite
  models.py           entidades e restrições relacionais
  schemas.py          contratos de entrada e validação
  auth.py             hash, emissão/verificação JWT e dependências de acesso
  routers/api.py      endpoints autenticados e operações transacionais
  services/finance.py regras de visibilidade, vínculos e divisão
  static/
    index.html        telas, formulários e diálogos
    style.css         layout responsivo e temas
    app.js            estado da interface e comunicação Fetch
    vendor/           Chart.js 4.4.8 e sua licença MIT
migrations/           evolução do esquema Alembic
scripts/              instalação e inicialização repetíveis
tests/                integração da API e smoke test opcional de navegador
docs/                 especificação, arquitetura e guia didático
```

## Modelo inicial implementado

- `grupos_familiares`: nome; um grupo tem usuários, contas e categorias.
- `usuarios`: grupo, nome, e-mail único, hash, papel, status, data de cadastro.
- `contas_bancarias`: grupo, nome e saldo inicial NUMERIC(14,2).
- `categorias`: grupo, nome e tipo; combinação única por grupo.
- `lancamentos`: grupo, responsável, pagador, conta, categoria, descrição, valor NUMERIC(14,2), tipo, vencimento, liquidação, compartilhamento, privacidade, modalidade e percentual de divisão, observações e cancelamento.
- `auditoria`: grupo, ator, ação, identificador e data. Registra criação de conta e criação, edição e cancelamento de lançamento; não contém senha/token. Não é ainda um histórico completo de versões ou uma trilha imutável externa.

Receitas e despesas usam a mesma tabela porque compartilham estrutura e ciclo de liquidação. A API distingue os tipos e valida a categoria. A participação do responsável e o restante do segundo integrante ficam no próprio lançamento: o MVP não exige tabelas separadas de receitas, despesas e divisões. O grupo diretamente no usuário expressa o vínculo único nesta etapa; múltiplos grupos exigirão `integrantes_grupo`.

Chaves estrangeiras impedem referências inexistentes; a camada de serviço verifica que as referências pertencem ao mesmo grupo. O cancelamento mantém referências e histórico. Operações de lançamento e auditoria usam a mesma sessão e commit, de forma atômica. Valores são `Decimal` no Python, `NUMERIC` no banco e strings no JSON para preservar centavos na transmissão. SQLite tem afinidade numérica, sem todas as garantias de precisão do NUMERIC do PostgreSQL; para produção e escalas maiores, usar PostgreSQL e testar seus limites.

## Regras e limites do MVP

1. Sem liquidação, o registro não altera o saldo.
2. Lançamento liquidado entra uma vez no saldo; editar substitui o dado usado no cálculo.
3. Despesa compartilhada é uma despesa única; divisão não cria despesas adicionais.
4. Quem paga recebe crédito no acerto; cada pessoa assume sua participação. Saldo positivo representa valor a receber.
5. Um centavo residual vai para o segundo integrante; a soma das parcelas permanece igual ao gasto.
6. Apenas o proprietário vê um lançamento privado. Administrador não ignora essa regra.
7. Integrante edita seus lançamentos; administrador gerencia registros visíveis, contas, categorias e o segundo integrante.
8. Não há transferência, pagamento de fatura ou cartão nesta etapa; esses eventos terão entidades próprias para não inflar receitas/despesas.
9. O saldo é derivado do histórico, não de incrementos mutáveis a cada requisição.

## Sequência de desenvolvimento

| Etapa | Entrega | Entidades futuras |
|---|---|---|
| 1 — atual | Login, grupo, contas, receitas/despesas, categorias, dashboard e divisão | Refinar convites, autorização, cadastro e histórico |
| 2 | Cartões, parcelas, recorrência, orçamento, calendário, contas a pagar | cartoes_credito, compras_cartao, parcelas_cartao, faturas, pagamentos_fatura, recorrencias, orcamentos, transferencias |
| 3 | Metas, dívidas, projeções, alertas, relatórios | metas_financeiras, contribuicoes_metas, dividas, parcelas_dividas, notificacoes |
| 4 | Importação, conciliação, exportação, backup, implantação e integrações | subcategorias, anexos protegidos, vínculos de integração e rotinas operacionais |

Cada evolução exige migração explícita e testes das invariantes financeiras. Pagamentos de fatura e transferências deverão movimentar caixa sem gerar novas despesas de consumo. Recorrências deverão possuir uma chave única por origem/período para impedir duplicação.
