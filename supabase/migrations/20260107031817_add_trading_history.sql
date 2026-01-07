
  create table "public"."trade_history" (
    "history_id" uuid not null default gen_random_uuid(),
    "trade_id" uuid not null default gen_random_uuid(),
    "root_trade_id" uuid not null default gen_random_uuid(),
    "sequence_number" smallint not null,
    "actor_user_id" text not null,
    "action" text not null,
    "details" jsonb not null,
    "created_at" timestamp with time zone not null default now()
      );


alter table "public"."trade_history" enable row level security;

alter table "public"."trade" drop column "completed_at";

alter table "public"."trade" drop column "updated_at";

alter table "public"."trade" add column "counter_count" smallint not null default '0'::smallint;

alter table "public"."trade" add column "initiator_confirmed" boolean not null default false;

alter table "public"."trade" add column "initiator_confirmed_at" timestamp with time zone;

alter table "public"."trade" add column "parent_trade_id" uuid default gen_random_uuid();

alter table "public"."trade" add column "recipient_confirmed" boolean not null default false;

alter table "public"."trade" add column "recipient_confirmed_at" timestamp with time zone;

alter table "public"."trade" add column "resolved_at" timestamp with time zone;

alter table "public"."trade" add column "root_trade_id" uuid default gen_random_uuid();

alter table "public"."trade" alter column "created_at" set not null;

alter table "public"."trade" alter column "initiator_inventory_id" set not null;

alter table "public"."trade" alter column "initiator_user_id" set not null;

alter table "public"."trade" alter column "recipient_inventory_id" set not null;

alter table "public"."trade" alter column "recipient_user_id" set not null;

alter table "public"."trade" alter column "status" set not null;

CREATE UNIQUE INDEX trade_history_pkey ON public.trade_history USING btree (history_id);

alter table "public"."trade_history" add constraint "trade_history_pkey" PRIMARY KEY using index "trade_history_pkey";

alter table "public"."trade" add constraint "trade_parent_trade_id_fkey" FOREIGN KEY (parent_trade_id) REFERENCES public.trade(trade_id) ON DELETE CASCADE not valid;

alter table "public"."trade" validate constraint "trade_parent_trade_id_fkey";

alter table "public"."trade" add constraint "trade_root_trade_id_fkey" FOREIGN KEY (root_trade_id) REFERENCES public.trade(trade_id) ON DELETE CASCADE not valid;

alter table "public"."trade" validate constraint "trade_root_trade_id_fkey";

alter table "public"."trade_history" add constraint "trade_history_actor_user_id_fkey" FOREIGN KEY (actor_user_id) REFERENCES public."user"(user_id) not valid;

alter table "public"."trade_history" validate constraint "trade_history_actor_user_id_fkey";

alter table "public"."trade_history" add constraint "trade_history_root_trade_id_fkey" FOREIGN KEY (root_trade_id) REFERENCES public.trade(trade_id) not valid;

alter table "public"."trade_history" validate constraint "trade_history_root_trade_id_fkey";

alter table "public"."trade_history" add constraint "trade_history_trade_id_fkey" FOREIGN KEY (trade_id) REFERENCES public.trade(trade_id) not valid;

alter table "public"."trade_history" validate constraint "trade_history_trade_id_fkey";

grant delete on table "public"."trade_history" to "anon";

grant insert on table "public"."trade_history" to "anon";

grant references on table "public"."trade_history" to "anon";

grant select on table "public"."trade_history" to "anon";

grant trigger on table "public"."trade_history" to "anon";

grant truncate on table "public"."trade_history" to "anon";

grant update on table "public"."trade_history" to "anon";

grant delete on table "public"."trade_history" to "authenticated";

grant insert on table "public"."trade_history" to "authenticated";

grant references on table "public"."trade_history" to "authenticated";

grant select on table "public"."trade_history" to "authenticated";

grant trigger on table "public"."trade_history" to "authenticated";

grant truncate on table "public"."trade_history" to "authenticated";

grant update on table "public"."trade_history" to "authenticated";

grant delete on table "public"."trade_history" to "postgres";

grant insert on table "public"."trade_history" to "postgres";

grant references on table "public"."trade_history" to "postgres";

grant select on table "public"."trade_history" to "postgres";

grant trigger on table "public"."trade_history" to "postgres";

grant truncate on table "public"."trade_history" to "postgres";

grant update on table "public"."trade_history" to "postgres";

grant delete on table "public"."trade_history" to "service_role";

grant insert on table "public"."trade_history" to "service_role";

grant references on table "public"."trade_history" to "service_role";

grant select on table "public"."trade_history" to "service_role";

grant trigger on table "public"."trade_history" to "service_role";

grant truncate on table "public"."trade_history" to "service_role";

grant update on table "public"."trade_history" to "service_role";


