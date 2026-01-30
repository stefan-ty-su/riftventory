alter table "public"."inventory" add column "is_private" boolean not null default false;


  create policy "Enable read access for all users"
  on "public"."card"
  as permissive
  for select
  to public
using (true);



  create policy "Enable users to create their own inventory"
  on "public"."inventory"
  as permissive
  for insert
  to authenticated
with check ((( SELECT auth.uid() AS uid) = user_id));



  create policy "Enable users to delete their own inventories"
  on "public"."inventory"
  as permissive
  for delete
  to authenticated
using ((( SELECT auth.uid() AS uid) = user_id));



  create policy "Enable users to update their own inventories"
  on "public"."inventory"
  as permissive
  for update
  to authenticated
using ((( SELECT auth.uid() AS uid) = user_id))
with check ((( SELECT auth.uid() AS uid) = user_id));



  create policy "Enable users to view their own and other public inventories"
  on "public"."inventory"
  as permissive
  for select
  to authenticated
using (((( SELECT auth.uid() AS uid) = user_id) OR (is_private = false)));



  create policy "Enable users to delete their own inventory cards"
  on "public"."inventory_card"
  as permissive
  for delete
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.inventory
  WHERE ((inventory.inventory_id = inventory_card.inventory_id) AND (inventory.user_id = auth.uid())))));



  create policy "Enable users to insert their own inventory cards"
  on "public"."inventory_card"
  as permissive
  for insert
  to authenticated
with check ((EXISTS ( SELECT 1
   FROM public.inventory
  WHERE ((inventory.inventory_id = inventory_card.inventory_id) AND (inventory.user_id = auth.uid())))));



  create policy "Enable users to update their own inventory cards"
  on "public"."inventory_card"
  as permissive
  for update
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.inventory
  WHERE ((inventory.inventory_id = inventory_card.inventory_id) AND (inventory.user_id = auth.uid())))))
with check ((EXISTS ( SELECT 1
   FROM public.inventory
  WHERE ((inventory.inventory_id = inventory_card.inventory_id) AND (inventory.user_id = auth.uid())))));



  create policy "Enable users to view theirs and others public inventory cards"
  on "public"."inventory_card"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.inventory
  WHERE ((inventory.inventory_id = inventory_card.inventory_id) AND ((inventory.user_id = auth.uid()) OR (inventory.is_private = false))))));



  create policy "Enable read access for all users"
  on "public"."set"
  as permissive
  for select
  to public
using (true);



  create policy "Enable trade participants to update the trade"
  on "public"."trade"
  as permissive
  for update
  to authenticated
using (((auth.uid() = initiator_user_id) OR (auth.uid() = recipient_user_id)))
with check (((auth.uid() = initiator_user_id) OR (auth.uid() = recipient_user_id)));



  create policy "Enable trade participants to view their trades"
  on "public"."trade"
  as permissive
  for select
  to authenticated
using (((auth.uid() = initiator_user_id) OR (auth.uid() = recipient_user_id)));



  create policy "Enable users to create trades"
  on "public"."trade"
  as permissive
  for insert
  to authenticated
with check ((auth.uid() = initiator_user_id));



  create policy "Enable trade initiators can manage escrow cards"
  on "public"."trade_escrow"
  as permissive
  for all
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_escrow.trade_id) AND (trade.initiator_user_id = auth.uid())))))
with check ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_escrow.trade_id) AND (trade.initiator_user_id = auth.uid())))));



  create policy "Enable trade participants to view escrow cards"
  on "public"."trade_escrow"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_escrow.trade_id) AND ((trade.initiator_user_id = auth.uid()) OR (trade.recipient_user_id = auth.uid()))))));



  create policy "Enable users to view their trade histories"
  on "public"."trade_history"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_history.trade_id) AND ((trade.initiator_user_id = auth.uid()) OR (trade.recipient_user_id = auth.uid()))))));



  create policy "Enable trade initiators can manage recipient items"
  on "public"."trade_recipient"
  as permissive
  for all
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_recipient.trade_id) AND (trade.initiator_user_id = auth.uid())))))
with check ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_recipient.trade_id) AND (trade.initiator_user_id = auth.uid())))));



  create policy "Enable trade participants to view requested items"
  on "public"."trade_recipient"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.trade
  WHERE ((trade.trade_id = trade_recipient.trade_id) AND ((trade.initiator_user_id = auth.uid()) OR (trade.recipient_user_id = auth.uid()))))));



  create policy "Enable users to update their own data only"
  on "public"."user"
  as permissive
  for update
  to authenticated
using ((( SELECT auth.uid() AS uid) = user_id))
with check ((( SELECT auth.uid() AS uid) = user_id));



  create policy "Enable users to view their own data only"
  on "public"."user"
  as permissive
  for select
  to authenticated
using ((( SELECT auth.uid() AS uid) = user_id));



