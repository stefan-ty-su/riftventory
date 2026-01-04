drop extension if exists "pg_net";


  create table "public"."card" (
    "set_id" text not null,
    "card_number" smallint not null,
    "card_id" text not null,
    "public_code" text not null,
    "card_name" text not null,
    "attr_energy" smallint,
    "attr_power" smallint,
    "attr_might" smallint,
    "card_type" text,
    "card_supertype" text,
    "card_rarity" text,
    "card_domain" text[],
    "text_rich" text,
    "text_plain" text,
    "card_image_url" text,
    "card_artist" text,
    "card_tags" text[],
    "orientation" text,
    "alternate_art" boolean default false,
    "overnumbered" boolean default false,
    "signature" boolean default false
      );


alter table "public"."card" enable row level security;


  create table "public"."inventory" (
    "inventory_id" uuid not null default gen_random_uuid(),
    "user_id" text not null,
    "inventory_name" text default 'My Inventory'::text,
    "inventory_colour" text,
    "created_at" timestamp with time zone,
    "last_updated" timestamp with time zone
      );


alter table "public"."inventory" enable row level security;


  create table "public"."inventory_card" (
    "inventory_id" uuid not null default gen_random_uuid(),
    "card_id" text not null,
    "quantity" smallint default '0'::smallint,
    "is_tradeable" boolean default false
      );


alter table "public"."inventory_card" enable row level security;


  create table "public"."set" (
    "id" text not null,
    "set_name" text not null,
    "set_id" text,
    "set_label" text,
    "card_count" smallint,
    "set_publish_date" timestamp without time zone
      );


alter table "public"."set" enable row level security;


  create table "public"."user" (
    "user_id" text not null,
    "created_at" timestamp with time zone not null default now(),
    "user_name" text not null
      );


alter table "public"."user" enable row level security;

CREATE UNIQUE INDEX card_pkey ON public.card USING btree (card_id);

CREATE UNIQUE INDEX card_public_code_key ON public.card USING btree (public_code);

CREATE UNIQUE INDEX inventory_card_pkey ON public.inventory_card USING btree (inventory_id, card_id);

CREATE UNIQUE INDEX inventory_pkey ON public.inventory USING btree (inventory_id);

CREATE UNIQUE INDEX set_pkey ON public.set USING btree (id);

CREATE UNIQUE INDEX set_set_id_key ON public.set USING btree (set_id);

CREATE UNIQUE INDEX set_set_label_key ON public.set USING btree (set_label);

CREATE UNIQUE INDEX user_pkey ON public."user" USING btree (user_id);

CREATE UNIQUE INDEX user_user_name_key ON public."user" USING btree (user_name);

alter table "public"."card" add constraint "card_pkey" PRIMARY KEY using index "card_pkey";

alter table "public"."inventory" add constraint "inventory_pkey" PRIMARY KEY using index "inventory_pkey";

alter table "public"."inventory_card" add constraint "inventory_card_pkey" PRIMARY KEY using index "inventory_card_pkey";

alter table "public"."set" add constraint "set_pkey" PRIMARY KEY using index "set_pkey";

alter table "public"."user" add constraint "user_pkey" PRIMARY KEY using index "user_pkey";

alter table "public"."card" add constraint "card_public_code_key" UNIQUE using index "card_public_code_key";

alter table "public"."card" add constraint "card_set_id_fkey" FOREIGN KEY (set_id) REFERENCES public.set(set_id) not valid;

alter table "public"."card" validate constraint "card_set_id_fkey";

alter table "public"."inventory" add constraint "inventory_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public."user"(user_id) ON DELETE CASCADE not valid;

alter table "public"."inventory" validate constraint "inventory_user_id_fkey";

alter table "public"."inventory_card" add constraint "inventory_card_card_id_fkey" FOREIGN KEY (card_id) REFERENCES public.card(card_id) ON UPDATE CASCADE not valid;

alter table "public"."inventory_card" validate constraint "inventory_card_card_id_fkey";

alter table "public"."inventory_card" add constraint "inventory_card_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES public.inventory(inventory_id) ON DELETE CASCADE not valid;

alter table "public"."inventory_card" validate constraint "inventory_card_inventory_id_fkey";

alter table "public"."set" add constraint "set_set_id_key" UNIQUE using index "set_set_id_key";

alter table "public"."set" add constraint "set_set_label_key" UNIQUE using index "set_set_label_key";

alter table "public"."user" add constraint "user_user_name_key" UNIQUE using index "user_user_name_key";

grant delete on table "public"."card" to "anon";

grant insert on table "public"."card" to "anon";

grant references on table "public"."card" to "anon";

grant select on table "public"."card" to "anon";

grant trigger on table "public"."card" to "anon";

grant truncate on table "public"."card" to "anon";

grant update on table "public"."card" to "anon";

grant delete on table "public"."card" to "authenticated";

grant insert on table "public"."card" to "authenticated";

grant references on table "public"."card" to "authenticated";

grant select on table "public"."card" to "authenticated";

grant trigger on table "public"."card" to "authenticated";

grant truncate on table "public"."card" to "authenticated";

grant update on table "public"."card" to "authenticated";

grant delete on table "public"."card" to "service_role";

grant insert on table "public"."card" to "service_role";

grant references on table "public"."card" to "service_role";

grant select on table "public"."card" to "service_role";

grant trigger on table "public"."card" to "service_role";

grant truncate on table "public"."card" to "service_role";

grant update on table "public"."card" to "service_role";

grant delete on table "public"."inventory" to "anon";

grant insert on table "public"."inventory" to "anon";

grant references on table "public"."inventory" to "anon";

grant select on table "public"."inventory" to "anon";

grant trigger on table "public"."inventory" to "anon";

grant truncate on table "public"."inventory" to "anon";

grant update on table "public"."inventory" to "anon";

grant delete on table "public"."inventory" to "authenticated";

grant insert on table "public"."inventory" to "authenticated";

grant references on table "public"."inventory" to "authenticated";

grant select on table "public"."inventory" to "authenticated";

grant trigger on table "public"."inventory" to "authenticated";

grant truncate on table "public"."inventory" to "authenticated";

grant update on table "public"."inventory" to "authenticated";

grant delete on table "public"."inventory" to "service_role";

grant insert on table "public"."inventory" to "service_role";

grant references on table "public"."inventory" to "service_role";

grant select on table "public"."inventory" to "service_role";

grant trigger on table "public"."inventory" to "service_role";

grant truncate on table "public"."inventory" to "service_role";

grant update on table "public"."inventory" to "service_role";

grant delete on table "public"."inventory_card" to "anon";

grant insert on table "public"."inventory_card" to "anon";

grant references on table "public"."inventory_card" to "anon";

grant select on table "public"."inventory_card" to "anon";

grant trigger on table "public"."inventory_card" to "anon";

grant truncate on table "public"."inventory_card" to "anon";

grant update on table "public"."inventory_card" to "anon";

grant delete on table "public"."inventory_card" to "authenticated";

grant insert on table "public"."inventory_card" to "authenticated";

grant references on table "public"."inventory_card" to "authenticated";

grant select on table "public"."inventory_card" to "authenticated";

grant trigger on table "public"."inventory_card" to "authenticated";

grant truncate on table "public"."inventory_card" to "authenticated";

grant update on table "public"."inventory_card" to "authenticated";

grant delete on table "public"."inventory_card" to "service_role";

grant insert on table "public"."inventory_card" to "service_role";

grant references on table "public"."inventory_card" to "service_role";

grant select on table "public"."inventory_card" to "service_role";

grant trigger on table "public"."inventory_card" to "service_role";

grant truncate on table "public"."inventory_card" to "service_role";

grant update on table "public"."inventory_card" to "service_role";

grant delete on table "public"."set" to "anon";

grant insert on table "public"."set" to "anon";

grant references on table "public"."set" to "anon";

grant select on table "public"."set" to "anon";

grant trigger on table "public"."set" to "anon";

grant truncate on table "public"."set" to "anon";

grant update on table "public"."set" to "anon";

grant delete on table "public"."set" to "authenticated";

grant insert on table "public"."set" to "authenticated";

grant references on table "public"."set" to "authenticated";

grant select on table "public"."set" to "authenticated";

grant trigger on table "public"."set" to "authenticated";

grant truncate on table "public"."set" to "authenticated";

grant update on table "public"."set" to "authenticated";

grant delete on table "public"."set" to "service_role";

grant insert on table "public"."set" to "service_role";

grant references on table "public"."set" to "service_role";

grant select on table "public"."set" to "service_role";

grant trigger on table "public"."set" to "service_role";

grant truncate on table "public"."set" to "service_role";

grant update on table "public"."set" to "service_role";

grant delete on table "public"."user" to "anon";

grant insert on table "public"."user" to "anon";

grant references on table "public"."user" to "anon";

grant select on table "public"."user" to "anon";

grant trigger on table "public"."user" to "anon";

grant truncate on table "public"."user" to "anon";

grant update on table "public"."user" to "anon";

grant delete on table "public"."user" to "authenticated";

grant insert on table "public"."user" to "authenticated";

grant references on table "public"."user" to "authenticated";

grant select on table "public"."user" to "authenticated";

grant trigger on table "public"."user" to "authenticated";

grant truncate on table "public"."user" to "authenticated";

grant update on table "public"."user" to "authenticated";

grant delete on table "public"."user" to "service_role";

grant insert on table "public"."user" to "service_role";

grant references on table "public"."user" to "service_role";

grant select on table "public"."user" to "service_role";

grant trigger on table "public"."user" to "service_role";

grant truncate on table "public"."user" to "service_role";

grant update on table "public"."user" to "service_role";


