# Configurar Supabase, passo a passo

## 1. Criar e identificar o projeto

No painel Supabase, crie um projeto na organização e região desejadas. Guarde a senha do PostgreSQL no gerenciador de segredos. Obtenha a **Project URL** e a chave **Publishable** (ou a antiga `anon`) nas configurações de API/API Keys. Configure `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` no runtime ou `.env` ignorado.

A chave publicável identifica o projeto, não autoriza acesso irrestrito aos dados. São o JWT do usuário e as políticas RLS que autorizam cada registro. Não coloque a senha do banco ou `service_role` no JavaScript, em screenshots, no chat, no Git ou em logs. Esta aplicação não necessita de service_role.

## 2. Configurar Auth

Em Authentication, habilite o provedor Email. Mantenha confirmação de e-mail em produção e configure SMTP para entrega confiável. Ajuste rate limits e CAPTCHA conforme a implantação; a integração do widget CAPTCHA é uma evolução caso você o habilite para signup/login.

Em URL Configuration, defina Site URL e redirects para a mesma origem `APP_URL`, com `/` no destino. Em desenvolvimento use a origem local; em produção use seu domínio HTTPS. A origem deve coincidir exatamente com a aplicação para que a verificação de Origin aceite as chamadas.

O signup usa o fluxo de e-mail padrão/implícito do Supabase, sem SDK no navegador. Após verificar o e-mail ou abrir o link de recuperação, o Supabase redireciona com tokens no fragmento `#`. O JavaScript remove imediatamente o fragmento da barra de endereço e envia os tokens a `/api/auth/callback`. O backend valida a identidade com o Auth, renova a sessão e guarda o refresh em cookie HttpOnly. Não configure templates de e-mail com fluxos PKCE/token_hash personalizados sem implementar o endpoint de troca correspondente.

O link de recuperação mostra um formulário para uma nova senha. O endpoint de atualização exige um access token validado pelo Supabase. Usuários já autenticados também podem alterar a própria senha pela API.

## 3. Criar tabelas e relações pelo SQL Editor

Instale as dependências e gere o pacote SQL:

```bash
bash scripts/setup.sh
.venv/bin/python scripts/migrate.py --sql > /tmp/rita-jean-supabase.sql
```

Abra **SQL Editor → New query** no projeto, cole o conteúdo gerado e execute como administrador do banco. O pacote não contém credenciais. Ele aplica somente migrações não registradas, verifica checksums e usa transações. Uma execução parcial pode ser repetida. O SQL é a fonte oficial do esquema; evite criar as mesmas tabelas manualmente no Table Editor.

As migrações versionadas são:

1. `202610160001_core.sql`: perfis ligados a `auth.users`, grupos, integrantes, contas, categorias, receitas, despesas, tabelas de planejamento e auditoria.
2. `202610160002_security.sql`: políticas RLS, rotinas restritas de criação do grupo/convite, índices de acesso já definidos no núcleo, auditoria e bloqueio de alterações de identidade.
3. `202610160003_storage_realtime.sql`: bucket privado, políticas por despesa e decisão explícita de manter Realtime financeiro desativado.

O Supabase já fornece `auth.users`, `auth.uid()`, `storage.buckets`, `storage.objects` e os papéis `anon`/`authenticated`. Não crie substitutos desses objetos no projeto hospedado. As versões simplificadas estão apenas no teste local.

Uma chave estrangeira é uma referência obrigatória: a despesa aponta para uma categoria e uma conta existentes. As chaves compostas `(family_id, account_id)` impedem apontar para a conta de outra família mesmo que seu UUID seja conhecido. Valores monetários usam `NUMERIC(15,2)`.

Verifique no SQL Editor:

```sql
select tablename, rowsecurity from pg_tables where schemaname = 'public';
select name, applied_at from private.schema_migrations order by name;
select id, name, public from storage.buckets where id = 'comprovantes';
```

**O SQL Editor roda com privilégios administrativos e pode ignorar RLS.** Ver tudo ali não significa que um usuário da aplicação tenha o mesmo acesso. Para verificar RLS, utilize o login de usuários diferentes ou a suíte de testes com `SET LOCAL ROLE authenticated`.

## 4. Conectar Python ao PostgreSQL

No botão **Connect** do projeto, obtenha o endereço Direct Connection ou **Session Pooler** compatível com a rede do servidor. Se sua infraestrutura não tem IPv6, o session pooler geralmente é a opção apropriada. Não use o Transaction Pooler nesta configuração sem validar compatibilidade com sessões/driver.

Preencha `DATABASE_URL` com o driver `postgresql+psycopg://`, usuário indicado no painel e senha URL-encoded. Exija `sslmode=verify-full`, baixe o certificado raiz indicado pelo Supabase ou use o conjunto de CAs confiáveis aplicável e configure `sslrootcert`. Não desative TLS, não use `sslmode=disable` nem reduza a validação para contornar erro de certificado.

O SQLAlchemy gerencia as sessões, e psycopg transporta consultas parametrizadas ao PostgreSQL. Valores de entrada não são concatenados em SQL. A string de conexão é exclusiva do servidor. Se preferir aplicar migrações por conexão direta em vez de SQL Editor:

```bash
.venv/bin/python scripts/migrate.py
```

As duas formas usam os mesmos checksums e histórico. As migrações exigem um usuário administrativo; a aplicação reduz cada transação ao papel `authenticated`. O usuário de conexão precisa poder assumir esse papel. Uma conexão como dono do banco sem essa redução pode ignorar RLS: não remova `FinanceSession` ou seu evento `after_begin`.

Se usar um papel de runtime dedicado, conceda somente a capacidade documentada de assumir `authenticated` e acesso mínimo de conexão; não use uma string de conexão que execute consultas como `service_role`. As migrações devem continuar numa conexão administrativa separada.

## 5. Storage privado e comprovantes

O bucket `comprovantes` é criado pela migração com limite de 5 MB e tipos PDF, PNG e JPEG. Não o torne público. Cada objeto recebe caminho `UUID-do-uploader/UUID-da-despesa/UUID-do-arquivo.ext`.

O FastAPI verifica se o usuário pode editar a despesa e envia o arquivo com o próprio JWT. O Storage verifica novamente o grupo e a privacidade consultando a despesa no banco. O download passa pelo FastAPI autenticado, mantém a verificação do Storage e força disposição de anexo. Não há URLs públicas permanentes nem necessidade de chave administrativa.

Na tela de despesas, salve a despesa, abra **Editar**, selecione o comprovante e envie. A assinatura básica do arquivo é verificada; a solução não faz análise antimalware.

## 6. Iniciar e testar no projeto real

```bash
bash scripts/start.sh
```

Verifique `/health/ready`, crie o primeiro usuário, confirme seu e-mail e entre. O primeiro acesso cria perfil, grupo, vínculo administrativo e categorias de maneira transacional. Gere um convite em Configurações. O segundo usuário informa o código no cadastro e confirma o e-mail antes de entrar; ele deve usar o convite antes do primeiro acesso criar outro grupo.

Teste: conta com saldo R$ 100; despesa pendente R$ 20 mantém R$ 100; liquidar resulta em R$ 80; editar para R$ 30 resulta em R$ 70; cancelar restaura R$ 100. Crie uma despesa privada e confirme que o outro usuário não a vê nem recebe seu impacto nos indicadores/saldos visíveis. Teste upload/download, recuperação de senha e renovação da sessão após recarregar.

Se um cadastro foi feito com convite inválido/expirado, gere outro e ajuste `invitation_code` nos metadados do próprio usuário no Auth por operação administrativa segura antes de tentar novamente. Não remova usuários com histórico financeiro; desative vínculos por operação administrativa planejada. O sistema não permite ao usuário se promover, mudar de grupo ou reativar seu vínculo via Data API.

## 7. Rede e diagnóstico

O servidor precisa de HTTPS para `SEU-PROJETO.supabase.co` (Auth/Storage) e acesso PostgreSQL ao host/porta Direct ou Session Pooler indicado em Connect. A liberação de um domínio HTTPS não garante acesso ao protocolo PostgreSQL. Em ambientes sem saída TCP para banco, use uma infraestrutura com conectividade suportada; não abra o banco publicamente ou desative verificações.

- `Configure as variáveis`: configure os quatro nomes do README.
- `Conexão PostgreSQL ou migrações indisponíveis`: verifique host/porta, DNS, SSL/certificado, senha e se o SQL foi aplicado.
- Falha de login: confirme e-mail, provedor Email, SMTP e limites do Auth.
- HTTP 403: verifique grupo, papel, RLS e origem `APP_URL`; não desative políticas para diagnosticar.
- Convite inválido: verifique validade, uso único e limite de dois integrantes.

Nenhuma configuração no repositório cria um projeto Supabase ou publica a aplicação automaticamente. O banco SQLite anterior não é convertido: IDs inteiros e usuários com senha local exigem um plano separado de importação e novo cadastro no Auth se houver dados a preservar.

## 8. Realtime e evolução

O MVP atual atualiza as telas com Fetch após cada operação. Não há necessidade de uma assinatura persistente ainda. Por isso nenhuma tabela financeira é adicionada automaticamente à publicação `supabase_realtime`. Evite ativar `REPLICA IDENTITY FULL` ou publicar eventos de exclusão que exponham linhas antigas privadas. Uma evolução deve usar canais privados e políticas revisadas, preferencialmente sinais de invalidação sem dados financeiros e nova consulta autenticada. Realtime não substitui RLS nem recalcula finanças no navegador.
