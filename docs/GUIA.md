# Primeiro módulo: do cadastro ao saldo do casal

## 1. O problema

Uma planilha pode misturar dinheiro previsto com dinheiro disponível e duplicar despesas quando uma pessoa paga pela outra. Este módulo registra a obrigação uma vez, guarda quem é responsável e quem pagou, e calcula a posição no backend.

## 2. Cadastro e autenticação

Leia o código completo de `app/schemas.py`, `app/models.py`, `app/auth.py` e os endpoints `/auth` de `app/routers/api.py`.

- **Schema** descreve a entrada: e-mail válido, senha com 10 a 128 caracteres e campos permitidos. Dados extras são rejeitados.
- **Modelo** descreve o armazenamento: `User` referencia `Family`. `password_hash` contém uma transformação Argon2, não a senha original.
- **Sessão SQLAlchemy** agrupa a criação do grupo, usuário e categorias; o commit confirma a unidade.
- **JWT** contém o identificador do usuário e expiração. O segredo é lido do ambiente. A dependência `current_user` valida a assinatura e busca o usuário ativo antes do endpoint.
- **Permissão** é verificada no servidor. Ocultar um botão não protege a API.

O frontend, em `app/static/app.js`, envia:

```javascript
fetch('/api/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'seu-email@example.com', password: 'sua-senha'})
});
```

A função `api()` adiciona o Bearer token nas próximas chamadas, trata erros de validação e encerra uma sessão inválida. O token fica na memória; o `localStorage` guarda somente a preferência de tema. Textos cadastrados são escapados antes de inserir HTML nas tabelas.

**Teste manual:** criar grupo, sair, tentar senha errada, entrar com a senha correta e cadastrar o segundo integrante. **Teste automático:** `test_auth_and_group_creation` e `test_expired_token`.

## 3. Contas e categorias

O administrador cria a conta com saldo inicial e as categorias por tipo. Leia `Account`, `Category`, os schemas de entrada e as rotas `/accounts` e `/categories`.

A conta não guarda um saldo atual que possa ficar dessincronizado: o endpoint calcula saldo inicial + receitas liquidadas − despesas liquidadas. Categoria usada no histórico não pode ser excluída; seu nome pode ser editado. Uma categoria de receita não pode ser usada numa despesa.

**Teste manual:** criar conta com R$ 100,00, adicionar uma despesa pendente de R$ 20,00 e verificar que o saldo continua R$ 100,00. **Teste automático:** `test_pending_and_settled_balances` e `test_validation_and_category_history`.

## 4. Lançamentos e privacidade

`EntryIn` valida valores positivos com duas casas decimais, datas e classificações. `validate_entry()` verifica cada vínculo com o grupo autenticado. `visible()` aplica a privacidade tanto às listas como aos totais e saldos.

O fluxo de salvamento é: formulário → JSON → Pydantic → validação de vínculos/permissões → lançamento + auditoria → commit → atualização da tela por Fetch. Editar utiliza PUT e mantém o identificador. Cancelar utiliza DELETE, mas só marca `cancelled=True`, preservando o registro e a auditoria.

Uma despesa privada é vista apenas pelo responsável. O administrador não pode criar uma despesa privada em nome de outra pessoa. Os saldos apresentados a cada usuário incluem somente seus registros visíveis; o texto da interface identifica essa limitação.

**Teste manual:** registrar R$ 20,00 como pago e conferir saldo R$ 80,00; editar para R$ 30,00 e conferir R$ 70,00; cancelar e conferir R$ 100,00. **Teste automático:** saldos, privacidade, permissões e isolamento em `tests/test_finance.py`.

## 5. Divisão e dashboard

Leia `app/services/finance.py`, especialmente `money()`, `validate_entry()` e `splits()`, e o endpoint `/dashboard`.

Se Rita é responsável e pagou R$ 1.000,00, com participação de 40%, a função calcula:

```python
own = money(amount * share_percent / 100)  # R$ 400,00 atribuídos à Rita
other = amount - own                      # R$ 600,00 atribuídos ao Jean
```

Rita assume R$ 400,00 e recebe crédito pelos R$ 1.000,00 pagos; seu acerto líquido é +R$ 600,00. Jean tem −R$ 600,00. O gasto consolidado continua R$ 1.000,00. Esse acerto não movimenta contas automaticamente.

A divisão igual força 50%. A proporcional usa a renda cadastrada para o mês de vencimento; se Rita tem R$ 2.000,00 e Jean R$ 3.000,00, a participação dela é 40%. Sem renda válida, a API retorna erro em vez de inventar proporção.

O dashboard consome valores já calculados pela API. Chart.js apenas desenha os gráficos e o JavaScript formata reais; ele não decide regras financeiras. Filtrar não altera os registros.

**Teste automático:** divisão com centavo residual, proporção 40/60 e cancelamento. Execute também o smoke test de navegador conforme o README.

## 6. Exercícios

1. Crie receitas de R$ 4.000 e R$ 6.000 e preveja o acerto de uma compra compartilhada de R$ 500 paga por Jean. Compare com a tela.
2. Cadastre uma receita futura e explique por que ela aparece nas receitas do mês, mas não aumenta o saldo.
3. Faça login como o outro integrante e compare os totais após uma despesa privada.
4. Leia o teste de isolamento e identifique por que trocar o `account_id` no JSON não permite acessar outro grupo.
5. Antes de desenvolver transferências na próxima etapa, escreva o resultado esperado: dois saldos mudam, mas receitas e despesas consolidadas permanecem iguais.

Não avance para cartões antes de manter esses testes passando. Regras novas devem continuar no backend e receber testes que detectem erros reais de dinheiro, permissão ou integridade.
