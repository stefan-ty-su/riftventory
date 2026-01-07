
  create table "public"."trade" (
    "trade_id" uuid not null default gen_random_uuid(),
    "initiator_user_id" text,
    "initiator_inventory_id" uuid default gen_random_uuid(),
    "recipient_user_id" text,
    "recipient_inventory_id" uuid default gen_random_uuid(),
    "status" text,
    "message" text,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "completed_at" timestamp with time zone
      );


alter table "public"."trade" enable row level security;


  create table "public"."trade_escrow" (
    "trade_id" uuid not null default gen_random_uuid(),
    "card_id" text not null,
    "quantity" smallint
      );


alter table "public"."trade_escrow" enable row level security;


  create table "public"."trade_recipient" (
    "trade_id" uuid not null default gen_random_uuid(),
    "card_id" text not null,
    "quantity" smallint
      );


alter table "public"."trade_recipient" enable row level security;

alter table "public"."inventory_card" add column "locked_quantity" smallint default '0'::smallint;

CREATE UNIQUE INDEX trade_escrow_pkey ON public.trade_escrow USING btree (trade_id, card_id);

CREATE UNIQUE INDEX trade_pkey ON public.trade USING btree (trade_id);

CREATE UNIQUE INDEX trade_recipient_pkey ON public.trade_recipient USING btree (trade_id, card_id);

alter table "public"."trade" add constraint "trade_pkey" PRIMARY KEY using index "trade_pkey";

alter table "public"."trade_escrow" add constraint "trade_escrow_pkey" PRIMARY KEY using index "trade_escrow_pkey";

alter table "public"."trade_recipient" add constraint "trade_recipient_pkey" PRIMARY KEY using index "trade_recipient_pkey";

alter table "public"."trade" add constraint "trade_initiator_inventory_id_fkey" FOREIGN KEY (initiator_inventory_id) REFERENCES public.inventory(inventory_id) ON DELETE CASCADE not valid;

alter table "public"."trade" validate constraint "trade_initiator_inventory_id_fkey";

alter table "public"."trade" add constraint "trade_initiator_user_id_fkey" FOREIGN KEY (initiator_user_id) REFERENCES public."user"(user_id) ON DELETE CASCADE not valid;

alter table "public"."trade" validate constraint "trade_initiator_user_id_fkey";

alter table "public"."trade" add constraint "trade_recipient_inventory_id_fkey" FOREIGN KEY (recipient_inventory_id) REFERENCES public.inventory(inventory_id) ON DELETE CASCADE not valid;

alter table "public"."trade" validate constraint "trade_recipient_inventory_id_fkey";

alter table "public"."trade" add constraint "trade_recipient_user_id_fkey" FOREIGN KEY (recipient_user_id) REFERENCES public."user"(user_id) ON DELETE CASCADE not valid;

alter table "public"."trade" validate constraint "trade_recipient_user_id_fkey";

alter table "public"."trade_escrow" add constraint "trade_escrow_card_id_fkey" FOREIGN KEY (card_id) REFERENCES public.card(card_id) ON DELETE CASCADE not valid;

alter table "public"."trade_escrow" validate constraint "trade_escrow_card_id_fkey";

alter table "public"."trade_escrow" add constraint "trade_escrow_trade_id_fkey" FOREIGN KEY (trade_id) REFERENCES public.trade(trade_id) ON DELETE CASCADE not valid;

alter table "public"."trade_escrow" validate constraint "trade_escrow_trade_id_fkey";

alter table "public"."trade_recipient" add constraint "trade_recipient_card_id_fkey" FOREIGN KEY (card_id) REFERENCES public.card(card_id) ON DELETE CASCADE not valid;

alter table "public"."trade_recipient" validate constraint "trade_recipient_card_id_fkey";

alter table "public"."trade_recipient" add constraint "trade_recipient_trade_id_fkey" FOREIGN KEY (trade_id) REFERENCES public.trade(trade_id) ON DELETE CASCADE not valid;

alter table "public"."trade_recipient" validate constraint "trade_recipient_trade_id_fkey";

grant delete on table "public"."trade" to "anon";

grant insert on table "public"."trade" to "anon";

grant references on table "public"."trade" to "anon";

grant select on table "public"."trade" to "anon";

grant trigger on table "public"."trade" to "anon";

grant truncate on table "public"."trade" to "anon";

grant update on table "public"."trade" to "anon";

grant delete on table "public"."trade" to "authenticated";

grant insert on table "public"."trade" to "authenticated";

grant references on table "public"."trade" to "authenticated";

grant select on table "public"."trade" to "authenticated";

grant trigger on table "public"."trade" to "authenticated";

grant truncate on table "public"."trade" to "authenticated";

grant update on table "public"."trade" to "authenticated";

grant delete on table "public"."trade" to "postgres";

grant insert on table "public"."trade" to "postgres";

grant references on table "public"."trade" to "postgres";

grant select on table "public"."trade" to "postgres";

grant trigger on table "public"."trade" to "postgres";

grant truncate on table "public"."trade" to "postgres";

grant update on table "public"."trade" to "postgres";

grant delete on table "public"."trade" to "service_role";

grant insert on table "public"."trade" to "service_role";

grant references on table "public"."trade" to "service_role";

grant select on table "public"."trade" to "service_role";

grant trigger on table "public"."trade" to "service_role";

grant truncate on table "public"."trade" to "service_role";

grant update on table "public"."trade" to "service_role";

grant delete on table "public"."trade_escrow" to "anon";

grant insert on table "public"."trade_escrow" to "anon";

grant references on table "public"."trade_escrow" to "anon";

grant select on table "public"."trade_escrow" to "anon";

grant trigger on table "public"."trade_escrow" to "anon";

grant truncate on table "public"."trade_escrow" to "anon";

grant update on table "public"."trade_escrow" to "anon";

grant delete on table "public"."trade_escrow" to "authenticated";

grant insert on table "public"."trade_escrow" to "authenticated";

grant references on table "public"."trade_escrow" to "authenticated";

grant select on table "public"."trade_escrow" to "authenticated";

grant trigger on table "public"."trade_escrow" to "authenticated";

grant truncate on table "public"."trade_escrow" to "authenticated";

grant update on table "public"."trade_escrow" to "authenticated";

grant delete on table "public"."trade_escrow" to "postgres";

grant insert on table "public"."trade_escrow" to "postgres";

grant references on table "public"."trade_escrow" to "postgres";

grant select on table "public"."trade_escrow" to "postgres";

grant trigger on table "public"."trade_escrow" to "postgres";

grant truncate on table "public"."trade_escrow" to "postgres";

grant update on table "public"."trade_escrow" to "postgres";

grant delete on table "public"."trade_escrow" to "service_role";

grant insert on table "public"."trade_escrow" to "service_role";

grant references on table "public"."trade_escrow" to "service_role";

grant select on table "public"."trade_escrow" to "service_role";

grant trigger on table "public"."trade_escrow" to "service_role";

grant truncate on table "public"."trade_escrow" to "service_role";

grant update on table "public"."trade_escrow" to "service_role";

grant delete on table "public"."trade_recipient" to "anon";

grant insert on table "public"."trade_recipient" to "anon";

grant references on table "public"."trade_recipient" to "anon";

grant select on table "public"."trade_recipient" to "anon";

grant trigger on table "public"."trade_recipient" to "anon";

grant truncate on table "public"."trade_recipient" to "anon";

grant update on table "public"."trade_recipient" to "anon";

grant delete on table "public"."trade_recipient" to "authenticated";

grant insert on table "public"."trade_recipient" to "authenticated";

grant references on table "public"."trade_recipient" to "authenticated";

grant select on table "public"."trade_recipient" to "authenticated";

grant trigger on table "public"."trade_recipient" to "authenticated";

grant truncate on table "public"."trade_recipient" to "authenticated";

grant update on table "public"."trade_recipient" to "authenticated";

grant delete on table "public"."trade_recipient" to "postgres";

grant insert on table "public"."trade_recipient" to "postgres";

grant references on table "public"."trade_recipient" to "postgres";

grant select on table "public"."trade_recipient" to "postgres";

grant trigger on table "public"."trade_recipient" to "postgres";

grant truncate on table "public"."trade_recipient" to "postgres";

grant update on table "public"."trade_recipient" to "postgres";

grant delete on table "public"."trade_recipient" to "service_role";

grant insert on table "public"."trade_recipient" to "service_role";

grant references on table "public"."trade_recipient" to "service_role";

grant select on table "public"."trade_recipient" to "service_role";

grant trigger on table "public"."trade_recipient" to "service_role";

grant truncate on table "public"."trade_recipient" to "service_role";

grant update on table "public"."trade_recipient" to "service_role";


