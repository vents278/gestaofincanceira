revoke create on schema public from public,anon,authenticated;
grant usage on schema public to authenticated;
-- Helpers have fixed search_path and narrowly scoped SECURITY DEFINER rights.
create function private.is_member(group_id uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.integrantes_grupo where family_id=group_id and user_id=auth.uid() and active)
$$;
create function private.is_admin(group_id uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.integrantes_grupo where family_id=group_id and user_id=auth.uid() and active and role='admin')
$$;
create function private.same_family(other_id uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.integrantes_grupo a join public.integrantes_grupo b on a.family_id=b.family_id
 where a.user_id=auth.uid() and a.active and b.user_id=other_id and b.active)
$$;
create function public.bootstrap_family(family_name text, invitation_code text default null) returns uuid
language plpgsql security definer set search_path='' as $$
declare group_id uuid; invitation private.convites; total int;
begin
 if auth.uid() is null then raise exception 'Authentication required' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text,0));
 insert into public.usuarios(id,name,email)
 select id, left(coalesce(nullif(trim(raw_user_meta_data->>'name'),''),'Integrante'),120),email
 from auth.users where id=auth.uid()
 on conflict(id) do update set name=excluded.name,email=excluded.email;
 select family_id into group_id from public.integrantes_grupo where user_id=auth.uid() and active;
 if found then return group_id; end if;
 if exists(select 1 from public.integrantes_grupo where user_id=auth.uid()) then
  raise exception 'Integrante inativo' using errcode='42501'; end if;
 if invitation_code is not null and invitation_code<>'' then
  select * into invitation from private.convites
   where token_hash=encode(sha256(convert_to(invitation_code,'UTF8')),'hex') and used_at is null and expires_at>now() for update;
  if not found then raise exception 'Convite inválido ou expirado' using errcode='22023'; end if;
  perform 1 from public.grupos_familiares where id=invitation.family_id for update;
  select count(*) into total from public.integrantes_grupo where family_id=invitation.family_id;
  if total>=2 then raise exception 'Grupo já possui dois integrantes' using errcode='22023'; end if;
  group_id:=invitation.family_id;
  insert into public.integrantes_grupo(family_id,user_id) values(group_id,auth.uid());
  update private.convites set used_at=now() where id=invitation.id;
 else
  if family_name is null or length(trim(family_name)) not between 2 and 120 then
   raise exception 'Informe o nome do grupo' using errcode='22023'; end if;
  insert into public.grupos_familiares(name,created_by) values(trim(family_name),auth.uid()) returning id into group_id;
  insert into public.integrantes_grupo(family_id,user_id,role) values(group_id,auth.uid(),'admin');
  insert into public.categorias(family_id,name,kind) values
   (group_id,'Salário','income'),(group_id,'Trabalho extra','income'),(group_id,'Rendimentos','income'),(group_id,'Outras receitas','income'),
   (group_id,'Moradia','expense'),(group_id,'Supermercado','expense'),(group_id,'Transporte','expense'),
   (group_id,'Saúde','expense'),(group_id,'Lazer','expense'),(group_id,'Outros','expense');
 end if;
 return group_id;
end $$;
create function public.create_family_invitation() returns text
language plpgsql security definer set search_path='' as $$
declare group_id uuid; code text;
begin
 select family_id into group_id from public.integrantes_grupo where user_id=auth.uid() and active and role='admin';
 if not found then raise exception 'Administrador necessário' using errcode='42501'; end if;
 perform 1 from public.grupos_familiares where id=group_id for update;
 if (select count(*) from public.integrantes_grupo where family_id=group_id)>=2 then
  raise exception 'Grupo já possui dois integrantes' using errcode='22023'; end if;
 update private.convites set used_at=now() where family_id=group_id and used_at is null;
 code:=gen_random_uuid()::text||gen_random_uuid()::text;
 insert into private.convites(family_id,token_hash) values(group_id,encode(sha256(convert_to(code,'UTF8')),'hex'));
 return code;
end $$;
-- Prevent identity swaps even when a caller bypasses FastAPI and calls Data API.
create function private.immutable_identity() returns trigger
language plpgsql set search_path='' as $$
begin
 if new.id<>old.id or new.family_id<>old.family_id then
  raise exception 'Identidade financeira imutável' using errcode='23514'; end if;
 return new;
end $$;
create function private.record_audit() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is not null then
  insert into public.auditoria(family_id,user_id,action,record_id)
  values(coalesce(new.family_id,old.family_id),auth.uid(),tg_table_name||'.'||lower(tg_op),coalesce(new.id,old.id));
 end if;
 return coalesce(new,old);
end $$;
alter table public.usuarios enable row level security;
revoke all on public.usuarios from anon, authenticated;
grant select on public.usuarios to authenticated;
alter table public.grupos_familiares enable row level security;
revoke all on public.grupos_familiares from anon, authenticated;
grant select on public.grupos_familiares to authenticated;
alter table public.integrantes_grupo enable row level security;
revoke all on public.integrantes_grupo from anon, authenticated;
grant select on public.integrantes_grupo to authenticated;
alter table public.contas_bancarias enable row level security;
revoke all on public.contas_bancarias from anon, authenticated;
grant select on public.contas_bancarias to authenticated;
alter table public.categorias enable row level security;
revoke all on public.categorias from anon, authenticated;
grant select on public.categorias to authenticated;
alter table public.receitas enable row level security;
revoke all on public.receitas from anon, authenticated;
grant select on public.receitas to authenticated;
alter table public.despesas enable row level security;
revoke all on public.despesas from anon, authenticated;
grant select on public.despesas to authenticated;
alter table public.cartoes_credito enable row level security;
revoke all on public.cartoes_credito from anon, authenticated;
grant select on public.cartoes_credito to authenticated;
alter table public.faturas enable row level security;
revoke all on public.faturas from anon, authenticated;
grant select on public.faturas to authenticated;
alter table public.parcelas enable row level security;
revoke all on public.parcelas from anon, authenticated;
grant select on public.parcelas to authenticated;
alter table public.metas_financeiras enable row level security;
revoke all on public.metas_financeiras from anon, authenticated;
grant select on public.metas_financeiras to authenticated;
alter table public.orcamentos enable row level security;
revoke all on public.orcamentos from anon, authenticated;
grant select on public.orcamentos to authenticated;
alter table public.anexos enable row level security;
revoke all on public.anexos from anon, authenticated;
grant select on public.anexos to authenticated;
alter table public.auditoria enable row level security;
revoke all on public.auditoria from anon, authenticated;
grant select on public.auditoria to authenticated;
alter table private.convites enable row level security;
create policy profile_read on public.usuarios for select to authenticated using(id=auth.uid() or private.same_family(id));
create policy family_read on public.grupos_familiares for select to authenticated using(private.is_member(id));
create policy member_read on public.integrantes_grupo for select to authenticated using(private.is_member(family_id));
create policy audit_read on public.auditoria for select to authenticated using(user_id=auth.uid() and private.is_member(family_id));
grant insert,update,delete on public.contas_bancarias to authenticated;
create policy contas_bancarias_read on public.contas_bancarias for select to authenticated using(private.is_member(family_id));
create policy contas_bancarias_insert on public.contas_bancarias for insert to authenticated with check(private.is_admin(family_id));
create policy contas_bancarias_update on public.contas_bancarias for update to authenticated using(private.is_admin(family_id)) with check(private.is_admin(family_id));
create policy contas_bancarias_delete on public.contas_bancarias for delete to authenticated using(private.is_admin(family_id));
grant insert,update,delete on public.categorias to authenticated;
create policy categorias_read on public.categorias for select to authenticated using(private.is_member(family_id));
create policy categorias_insert on public.categorias for insert to authenticated with check(private.is_admin(family_id));
create policy categorias_update on public.categorias for update to authenticated using(private.is_admin(family_id)) with check(private.is_admin(family_id));
create policy categorias_delete on public.categorias for delete to authenticated using(private.is_admin(family_id));
grant insert,update,delete on public.cartoes_credito to authenticated;
create policy cartoes_credito_read on public.cartoes_credito for select to authenticated using(private.is_member(family_id));
create policy cartoes_credito_insert on public.cartoes_credito for insert to authenticated with check(private.is_admin(family_id));
create policy cartoes_credito_update on public.cartoes_credito for update to authenticated using(private.is_admin(family_id)) with check(private.is_admin(family_id));
create policy cartoes_credito_delete on public.cartoes_credito for delete to authenticated using(private.is_admin(family_id));
grant insert,update,delete on public.faturas to authenticated;
create policy faturas_read on public.faturas for select to authenticated using(private.is_member(family_id));
create policy faturas_insert on public.faturas for insert to authenticated with check(private.is_admin(family_id));
create policy faturas_update on public.faturas for update to authenticated using(private.is_admin(family_id)) with check(private.is_admin(family_id));
create policy faturas_delete on public.faturas for delete to authenticated using(private.is_admin(family_id));
grant insert,update on public.receitas to authenticated;
create policy receitas_read on public.receitas for select to authenticated using(private.is_member(family_id) and (not private or owner_id=auth.uid()));
create policy receitas_insert on public.receitas for insert to authenticated with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
create policy receitas_update on public.receitas for update to authenticated using((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id))) with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
grant insert,update on public.despesas to authenticated;
create policy despesas_read on public.despesas for select to authenticated using(private.is_member(family_id) and (not private or owner_id=auth.uid()));
create policy despesas_insert on public.despesas for insert to authenticated with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
create policy despesas_update on public.despesas for update to authenticated using((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id))) with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
grant insert,update on public.metas_financeiras to authenticated;
create policy metas_financeiras_read on public.metas_financeiras for select to authenticated using(private.is_member(family_id) and (not private or owner_id=auth.uid()));
create policy metas_financeiras_insert on public.metas_financeiras for insert to authenticated with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
create policy metas_financeiras_update on public.metas_financeiras for update to authenticated using((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id))) with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
grant delete on public.metas_financeiras to authenticated;
create policy metas_financeiras_delete on public.metas_financeiras for delete to authenticated using((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
grant insert,update on public.orcamentos to authenticated;
create policy orcamentos_read on public.orcamentos for select to authenticated using(private.is_member(family_id) and (not private or owner_id=auth.uid()));
create policy orcamentos_insert on public.orcamentos for insert to authenticated with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
create policy orcamentos_update on public.orcamentos for update to authenticated using((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id))) with check((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
grant delete on public.orcamentos to authenticated;
create policy orcamentos_delete on public.orcamentos for delete to authenticated using((private.is_member(family_id) and (not private or owner_id=auth.uid())) and (owner_id=auth.uid() or private.is_admin(family_id)));
create policy installment_read on public.parcelas for select to authenticated using(
 private.is_member(family_id) and exists(select 1 from public.despesas e where e.id=expense_id));
grant insert,update,delete on public.parcelas to authenticated;
create policy installment_write on public.parcelas for all to authenticated
 using(private.is_admin(family_id) and exists(select 1 from public.despesas e where e.id=expense_id))
 with check(private.is_admin(family_id) and exists(select 1 from public.despesas e where e.id=expense_id));
create policy attachment_read on public.anexos for select to authenticated using(
 private.is_member(family_id) and exists(select 1 from public.despesas e where e.id=expense_id));
grant insert,delete on public.anexos to authenticated;
create policy attachment_insert on public.anexos for insert to authenticated with check(
 owner_id=auth.uid() and private.is_member(family_id) and exists(select 1 from public.despesas e where e.id=expense_id and (e.owner_id=auth.uid() or private.is_admin(e.family_id))));
create policy attachment_delete on public.anexos for delete to authenticated using(
 owner_id=auth.uid() and private.is_member(family_id) and exists(select 1 from public.despesas e where e.id=expense_id));
create trigger immutable_contas_bancarias before update on public.contas_bancarias for each row execute function private.immutable_identity();
create trigger audit_contas_bancarias after insert or update or delete on public.contas_bancarias for each row execute function private.record_audit();
create trigger immutable_categorias before update on public.categorias for each row execute function private.immutable_identity();
create trigger audit_categorias after insert or update or delete on public.categorias for each row execute function private.record_audit();
create trigger immutable_receitas before update on public.receitas for each row execute function private.immutable_identity();
create trigger audit_receitas after insert or update or delete on public.receitas for each row execute function private.record_audit();
create trigger immutable_despesas before update on public.despesas for each row execute function private.immutable_identity();
create trigger audit_despesas after insert or update or delete on public.despesas for each row execute function private.record_audit();
create trigger immutable_cartoes_credito before update on public.cartoes_credito for each row execute function private.immutable_identity();
create trigger audit_cartoes_credito after insert or update or delete on public.cartoes_credito for each row execute function private.record_audit();
create trigger immutable_faturas before update on public.faturas for each row execute function private.immutable_identity();
create trigger audit_faturas after insert or update or delete on public.faturas for each row execute function private.record_audit();
create trigger immutable_parcelas before update on public.parcelas for each row execute function private.immutable_identity();
create trigger audit_parcelas after insert or update or delete on public.parcelas for each row execute function private.record_audit();
create trigger immutable_metas_financeiras before update on public.metas_financeiras for each row execute function private.immutable_identity();
create trigger audit_metas_financeiras after insert or update or delete on public.metas_financeiras for each row execute function private.record_audit();
create trigger immutable_orcamentos before update on public.orcamentos for each row execute function private.immutable_identity();
create trigger audit_orcamentos after insert or update or delete on public.orcamentos for each row execute function private.record_audit();
create trigger immutable_anexos before update on public.anexos for each row execute function private.immutable_identity();
create trigger audit_anexos after insert or update or delete on public.anexos for each row execute function private.record_audit();
-- Definer helpers are callable only by authenticated roles; never allow anonymous bootstrap.
revoke all on all functions in schema private from public,anon;
grant execute on function private.is_member(uuid),private.is_admin(uuid),private.same_family(uuid) to authenticated;
revoke all on function public.bootstrap_family(text,text),public.create_family_invitation() from public,anon;
grant execute on function public.bootstrap_family(text,text),public.create_family_invitation() to authenticated;
