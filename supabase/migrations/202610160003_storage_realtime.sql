-- Private receipts: paths are uploader UUID / expense UUID / object UUID.ext.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('comprovantes','comprovantes',false,5242880,array['image/png','image/jpeg','application/pdf']);
create function private.can_access_receipt(object_name text, write_access boolean default false) returns boolean
language plpgsql stable security definer set search_path='' as $$
declare parts text[]; expense public.despesas;
begin
 parts:=string_to_array(object_name,'/');
 if array_length(parts,1)<>3 then return false; end if;
 select * into expense from public.despesas where id=parts[2]::uuid;
 if not found or expense.cancelled or not private.is_member(expense.family_id)
  or (expense.private and expense.owner_id<>auth.uid()) then return false; end if;
 if write_access then
  return parts[1]=auth.uid()::text and (expense.owner_id=auth.uid() or private.is_admin(expense.family_id));
 end if;
 return true;
exception when invalid_text_representation then return false;
end $$;
revoke all on function private.can_access_receipt(text,boolean) from public,anon;
grant execute on function private.can_access_receipt(text,boolean) to authenticated;
create policy receipt_read on storage.objects for select to authenticated using(
 bucket_id='comprovantes' and private.can_access_receipt(name,false));
create policy receipt_insert on storage.objects for insert to authenticated with check(
 bucket_id='comprovantes' and private.can_access_receipt(name,true));
create policy receipt_delete on storage.objects for delete to authenticated using(
 bucket_id='comprovantes' and private.can_access_receipt(name,true));
-- No UPDATE/upsert: receipts are immutable objects. Replacing creates a new UUID.
-- Realtime is opt-in. Do NOT publish financial row changes by default: DELETE
-- payloads cannot be filtered by RLS, and OLD rows can reveal private history.
