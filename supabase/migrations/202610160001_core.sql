-- Supabase PostgreSQL 15+. Run in order, in a transaction.
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;
create table public.usuarios (
 id uuid primary key references auth.users(id) on delete cascade,
 name varchar(120) not null,
 email varchar(254) not null,
 created_at timestamptz not null default now()
);
create table public.grupos_familiares (
 id uuid primary key default gen_random_uuid(),
 name varchar(120) not null check (length(trim(name)) >= 2),
 created_by uuid not null references public.usuarios(id),
 created_at timestamptz not null default now()
);
create table public.integrantes_grupo (
 id uuid primary key default gen_random_uuid(),
 family_id uuid not null references public.grupos_familiares(id),
 user_id uuid not null unique references public.usuarios(id),
 role text not null default 'member' check (role in ('admin','member')),
 active boolean not null default true,
 unique(family_id,user_id)
);
create index members_family on public.integrantes_grupo(family_id);
create table private.convites (
 id uuid primary key default gen_random_uuid(),
 family_id uuid not null references public.grupos_familiares(id),
 token_hash text not null unique,
 expires_at timestamptz not null default now()+interval '48 hours',
 used_at timestamptz
);
create table public.contas_bancarias (
 id uuid primary key default gen_random_uuid(),
 family_id uuid not null references public.grupos_familiares(id),
 name varchar(120) not null,
 initial_balance numeric(15,2) not null default 0,
 unique(family_id,id)
);
create table public.categorias (
 id uuid primary key default gen_random_uuid(),
 family_id uuid not null references public.grupos_familiares(id),
 name varchar(120) not null,
 kind text not null check (kind in ('income','expense')),
 unique(family_id,name,kind), unique(family_id,id,kind)
);
create table public.receitas (
 id uuid primary key default gen_random_uuid(),
 family_id uuid not null references public.grupos_familiares(id),
 owner_id uuid not null,
 payer_id uuid not null,
 account_id uuid not null,
 category_id uuid not null,
 kind text not null default 'income' check(kind='income'),
 description varchar(200) not null check(length(trim(description))>=2),
 amount numeric(15,2) not null check(amount>0),
 due_date date not null,
 settled_date date check(settled_date<=current_date),
 shared boolean not null default false,
 private boolean not null default false,
 split_mode text not null default 'equal' check(split_mode in ('equal','custom','proportional')),
 share_percent numeric(5,2) not null default 50 check(share_percent between 0 and 100),
 notes varchar(2000) not null default '',
 cancelled boolean not null default false,
 check(not shared or (not private and kind='expense')),
 check(not shared or split_mode<>'equal' or share_percent=50),
 foreign key(family_id,owner_id) references public.integrantes_grupo(family_id,user_id),
 foreign key(family_id,payer_id) references public.integrantes_grupo(family_id,user_id),
 foreign key(family_id,account_id) references public.contas_bancarias(family_id,id),
 foreign key(family_id,category_id,kind) references public.categorias(family_id,id,kind),
 unique(family_id,id)
);
create index receitas_family_date on public.receitas(family_id,due_date);
create index receitas_owner_date on public.receitas(owner_id,due_date);
create index receitas_category on public.receitas(category_id);
create index receitas_account on public.receitas(account_id);
create table public.despesas (
 id uuid primary key default gen_random_uuid(),
 family_id uuid not null references public.grupos_familiares(id),
 owner_id uuid not null,
 payer_id uuid not null,
 account_id uuid not null,
 category_id uuid not null,
 kind text not null default 'expense' check(kind='expense'),
 description varchar(200) not null check(length(trim(description))>=2),
 amount numeric(15,2) not null check(amount>0),
 due_date date not null,
 settled_date date check(settled_date<=current_date),
 shared boolean not null default false,
 private boolean not null default false,
 split_mode text not null default 'equal' check(split_mode in ('equal','custom','proportional')),
 share_percent numeric(5,2) not null default 50 check(share_percent between 0 and 100),
 notes varchar(2000) not null default '',
 cancelled boolean not null default false,
 check(not shared or (not private and kind='expense')),
 check(not shared or split_mode<>'equal' or share_percent=50),
 foreign key(family_id,owner_id) references public.integrantes_grupo(family_id,user_id),
 foreign key(family_id,payer_id) references public.integrantes_grupo(family_id,user_id),
 foreign key(family_id,account_id) references public.contas_bancarias(family_id,id),
 foreign key(family_id,category_id,kind) references public.categorias(family_id,id,kind),
 unique(family_id,id)
);
create index despesas_family_date on public.despesas(family_id,due_date);
create index despesas_owner_date on public.despesas(owner_id,due_date);
create index despesas_category on public.despesas(category_id);
create index despesas_account on public.despesas(account_id);
create table public.cartoes_credito (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 owner_id uuid not null, account_id uuid not null, name varchar(120) not null,
 credit_limit numeric(15,2) not null check(credit_limit>=0),
 closing_day int not null check(closing_day between 1 and 31), due_day int not null check(due_day between 1 and 31),
 foreign key(family_id,owner_id) references public.integrantes_grupo(family_id,user_id),
 foreign key(family_id,account_id) references public.contas_bancarias(family_id,id), unique(family_id,id)
);
create table public.faturas (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 card_id uuid not null, due_date date not null, status text not null default 'open' check(status in ('open','closed','paid')),
 foreign key(family_id,card_id) references public.cartoes_credito(family_id,id), unique(card_id,due_date), unique(family_id,id)
);
create table public.parcelas (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 invoice_id uuid not null, expense_id uuid not null, number int not null check(number>0),
 amount numeric(15,2) not null check(amount>0), due_date date not null,
 foreign key(family_id,invoice_id) references public.faturas(family_id,id),
 foreign key(family_id,expense_id) references public.despesas(family_id,id), unique(expense_id,number)
);
create table public.metas_financeiras (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 owner_id uuid not null, name varchar(120) not null, target numeric(15,2) not null check(target>0),
 accumulated numeric(15,2) not null default 0 check(accumulated>=0), deadline date not null, private boolean not null default false,
 foreign key(family_id,owner_id) references public.integrantes_grupo(family_id,user_id)
);
create table public.orcamentos (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 owner_id uuid not null, category_id uuid not null, kind text not null default 'expense' check(kind='expense'),
 month date not null check(extract(day from month)=1), amount numeric(15,2) not null check(amount>0), private boolean not null default false,
 foreign key(family_id,owner_id) references public.integrantes_grupo(family_id,user_id),
 foreign key(family_id,category_id,kind) references public.categorias(family_id,id,kind), unique(family_id,owner_id,category_id,month)
);
create table public.anexos (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 owner_id uuid not null references public.usuarios(id), expense_id uuid not null,
 object_path text not null unique, filename varchar(200) not null, content_type text not null,
 created_at timestamptz not null default now(),
 foreign key(family_id,expense_id) references public.despesas(family_id,id)
);
create table public.auditoria (
 id uuid primary key default gen_random_uuid(), family_id uuid not null references public.grupos_familiares(id),
 user_id uuid not null references public.usuarios(id), action varchar(100) not null, record_id uuid not null,
 created_at timestamptz not null default now()
);
create index contas_bancarias_family on public.contas_bancarias(family_id);
create index categorias_family on public.categorias(family_id);
create index cartoes_credito_family on public.cartoes_credito(family_id);
create index faturas_family on public.faturas(family_id);
create index parcelas_family on public.parcelas(family_id);
create index metas_financeiras_family on public.metas_financeiras(family_id);
create index orcamentos_family on public.orcamentos(family_id);
create index anexos_family on public.anexos(family_id);
create index auditoria_family on public.auditoria(family_id);
create index cards_owner on public.cartoes_credito(owner_id);
create index invoices_date on public.faturas(due_date);
create index installments_date on public.parcelas(due_date);
create index goals_owner on public.metas_financeiras(owner_id);
create index budget_owner_month on public.orcamentos(owner_id,month);
create index budget_category on public.orcamentos(category_id);
create index attachments_expense on public.anexos(expense_id);
create index audit_actor_date on public.auditoria(user_id,created_at);
