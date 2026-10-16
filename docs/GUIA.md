# Guia didático dos módulos Supabase

A especificação financeira original está em `ESPECIFICACAO.md`. Esta alteração substitui sua infraestrutura local por Supabase. O código completo está nos arquivos listados a seguir; não há trechos ocultos ou dependência de código gerado fora do repositório.

## 1. Identidade, cadastro e sessão

**Problema:** cada integrante precisa de uma identidade segura, e o sistema não deve administrar senhas locais.

**Arquivos:** `app/auth.py` comunica-se com Supabase; `app/routers/auth.py` expõe os fluxos ao navegador; `app/config.py` valida configuração; `app/static/app.js` controla formulários e sessão.

O cadastro envia e-mail e senha a `/api/auth/register`. O backend encaminha ao endpoint de signup do Supabase. Nome e preferência de grupo ficam em metadados, mas não concedem privilégio. Quando há confirmação de e-mail, o frontend informa a pendência sem inventar uma sessão.

No login, Supabase fornece access token e refresh token. `session_response()` devolve somente o access token ao JavaScript e guarda o refresh em cookie HttpOnly. O navegador usa `Authorization: Bearer ...` nas requisições; `/api/auth/refresh` renova o token, inclusive após recarregar a página. JavaScript não consegue ler o cookie HttpOnly.

`verify_access()` chama `/auth/v1/user`: é o Supabase que verifica o token. O UUID retornado é o único aceito para o contexto financeiro. `current_user()` obtém nome e papel do banco, não do corpo da requisição. Recuperação usa o e-mail do Supabase e uma sessão validada para atualizar a senha.

**Como testar:** cadastro, confirmação, login incorreto/correto, reload, recuperação e logout. Os testes de contrato estão em `tests/test_supabase_auth.py`; a entrega real de e-mail só pode ser comprovada no projeto hospedado.

**Exercício:** explique por que enviar `role: 'admin'` em metadados não deveria conceder acesso administrativo. Localize a consulta ao vínculo no banco que impede isso.

## 2. Grupos e convites

**Problema:** duas pessoas devem compartilhar um grupo sem compartilhar senha ou poder se adicionar arbitrariamente ao grupo de terceiros.

**Arquivos:** `supabase/migrations/202610160002_security.sql`, `app/dependencies.py`, `/members/invitations` em `app/routers/api.py` e o formulário de configurações.

`bootstrap_family()` cria o perfil referenciando `auth.users`, grupo e vínculo administrativo numa transação. Alternativamente, consome um convite válido, entra como integrante e marca o código como usado. Travas de transação/linha evitam duplicar o bootstrap ou inserir um terceiro integrante simultaneamente. O banco armazena o hash do convite, não o código em claro.

A função usa `SECURITY DEFINER` porque precisa criar o primeiro vínculo antes de o usuário ser membro. Esse privilégio fica limitado: `auth.uid()` deve existir, a rotina valida o convite, e o `search_path` vazio evita substituição maliciosa de objetos. Nenhum usuário pode alterar diretamente `integrantes_grupo` pela Data API.

**Como testar:** gerar convite, cadastrar segunda pessoa com ele, tentar reutilizar o código e tentar criar outro convite com o grupo cheio. Consulte também os testes SQL que tentam editar a própria role.

**Exercício:** identifique a diferença entre uma política RLS e uma restrição de integridade. Por que ambas são úteis para proteger o grupo?

## 3. Python, PostgreSQL e RLS

**Problema:** esconder botões ou filtrar apenas no JavaScript não impede uma chamada manual à API de acessar dados privados.

**Arquivos:** `app/database.py`, `app/models.py`, as migrações `core` e `security`, `tests/test_rls.py`.

O SQLAlchemy mapeia classes às tabelas; psycopg abre a conexão PostgreSQL. O evento `after_begin` executa em cada nova transação:

```python
connection.exec_driver_sql('SET LOCAL ROLE authenticated')
connection.exec_driver_sql(
    "SELECT set_config('request.jwt.claims', %s, true)",
    (json.dumps({'sub': str(user_id), 'role': 'authenticated'}),),
)
```

A primeira instrução reduz o papel. A segunda informa a identidade já validada; `%s` é parâmetro, não interpolação de entrada em SQL. O `true` torna a configuração local à transação. Assim, `auth.uid()` nas políticas aponta para a pessoa correta e o pool não reaproveita sua identidade em outra requisição.

Uma política como `private.is_member(family_id) AND (NOT private OR owner_id=auth.uid())` permite ver um registro público do grupo ou o próprio privado. A política de escrita também exige propriedade ou papel administrativo. Mesmo o administrador não lê privados de outra pessoa.

**Como testar:** a suíte usa PostgreSQL real e `SET LOCAL ROLE authenticated`, sem helpers da API, para tentar consultar, inserir e editar registros indevidos. Um teste adicional confirma o contexto após `commit` e troca de conexão.

**Exercício:** remova o filtro de grupo de uma consulta em um ambiente descartável e veja por que RLS ainda bloqueia outras famílias. Nunca altere RLS em produção para fazer esse experimento.

## 4. Receitas, despesas e cálculos

**Problema:** diferenciar previsão de dinheiro liquidado e dividir gastos sem duplicar o total.

**Arquivos:** `app/schemas.py`, `app/services/finance.py`, `app/routers/api.py`, modelos `Income` e `Expense` e as tabelas `receitas`/`despesas`.

O schema exige UUIDs válidos, valor positivo e no máximo duas casas decimais. O serviço verifica vínculos com o mesmo grupo e categoria do tipo certo. As FKs compostas repetem essa garantia no banco, inclusive para chamadas diretas à Data API.

O saldo é derivado: saldo inicial + receitas liquidadas − despesas liquidadas. Não existe um segundo saldo acumulado sujeito a duplicação por reenvio. Editar substitui o dado considerado no cálculo; cancelar marca o registro. Triggers registram a ação na mesma transação, inclusive quando uma escrita ocorre fora do FastAPI.

Para despesa de R$ 1.000 paga por Rita, com 40% para ela, `money(amount * share_percent / 100)` calcula R$ 400. Jean assume os R$ 600 restantes. Rita recebe crédito pelo total que pagou e tem R$ 600 a receber; o gasto consolidado continua R$ 1.000. Esse acerto não realiza transferência entre contas.

**Frontend:** o formulário envia JSON por Fetch; o backend devolve valores decimais como strings. Chart.js só desenha e o JavaScript só formata reais. Os cálculos de saldo e divisão nunca dependem do navegador.

**Como testar:** os testes financeiros cobrem pendência, liquidação, edição repetida, cancelamento, proporção 40/60, centavo residual e privacidade. Compare manualmente com o roteiro do README.

**Exercício:** com rendas de R$ 4.000 e R$ 6.000, calcule o acerto de uma despesa compartilhada de R$ 500 paga por Jean. Verifique o resultado no dashboard.

## 5. Comprovantes e Storage

**Problema:** um comprovante pode conter dados bancários e não pode ficar em uma URL pública.

**Arquivos:** `app/routers/storage.py`, tabela `anexos`, migração `202610160003_storage_realtime.sql` e seção de comprovantes no diálogo de edição.

O frontend envia o corpo binário com `Content-Type` e nome do arquivo. O backend limita a 5 MB e verifica a assinatura básica PDF/PNG/JPEG. O arquivo recebe um UUID e é enviado com o JWT do usuário para `comprovantes`, um bucket privado. A política do Storage consulta a despesa e seu grupo/privacidade. O download também exige o JWT e usa disposição `attachment`.

Storage HTTP e metadados PostgreSQL não compartilham uma transação distribuída. Se gravar o objeto e o banco falhar, a aplicação tenta removê-lo; uma rotina de conciliação será necessária para tratar órfãos após falhas de rede. Não existe antivírus nesta etapa.

**Como testar:** `tests/test_storage.py` valida o endpoint com HTTP do Storage simulado; `test_storage_policy_matches_expense_privacy` valida a política SQL real. O teste final de upload/download no bucket hospedado ainda exige as credenciais do projeto.

**Exercício:** explique por que tornar o bucket público invalidaria a expectativa de privacidade mesmo que a API continuasse protegida.

## 6. Evoluir com migrações

O SQL versionado é a fonte oficial do esquema. Não altere um arquivo já aplicado: crie uma nova migração. O runner verifica SHA-256 e recusa divergências. O pacote `--sql` permite executar o mesmo histórico no SQL Editor.

Cartões, faturas, parcelas, metas e orçamentos já têm fundação relacional e RLS, mas suas telas e automações serão implementadas em etapas próprias. Pagamento de fatura e transferência não devem criar receita/despesa de consumo. Realtime ficará para um fluxo que realmente precise dele, com autorização de canais e proteção de dados antigos.
