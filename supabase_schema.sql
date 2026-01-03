-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.card (
  set_id text NOT NULL,
  card_number smallint NOT NULL,
  card_id text NOT NULL UNIQUE,
  public_code text NOT NULL UNIQUE,
  card_name text NOT NULL,
  attr_energy smallint,
  attr_power smallint,
  attr_might smallint,
  card_type text,
  card_supertype text,
  card_rarity text,
  card_domain ARRAY,
  text_rich text,
  text_plain text,
  card_image_url text,
  card_artist text,
  card_tags ARRAY,
  orientation text,
  alternate_art boolean DEFAULT false,
  overnumbered boolean DEFAULT false,
  signature boolean DEFAULT false,
  CONSTRAINT card_pkey PRIMARY KEY (card_id),
  CONSTRAINT card_set_id_fkey FOREIGN KEY (set_id) REFERENCES public.set(set_id)
);
CREATE TABLE public.inventory (
  inventory_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  inventory_name text DEFAULT 'My Inventory'::text,
  inventory_colour text,
  created_at timestamp with time zone,
  last_updated timestamp with time zone,
  CONSTRAINT inventory_pkey PRIMARY KEY (inventory_id),
  CONSTRAINT inventory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user(user_id)
);
CREATE TABLE public.inventory_card (
  inventory_id uuid NOT NULL DEFAULT gen_random_uuid(),
  card_id text NOT NULL,
  quantity smallint DEFAULT '0'::smallint,
  is_tradeable boolean DEFAULT false,
  CONSTRAINT inventory_card_pkey PRIMARY KEY (inventory_id, card_id),
  CONSTRAINT inventory_card_inventory_id_fkey FOREIGN KEY (inventory_id) REFERENCES public.inventory(inventory_id),
  CONSTRAINT inventory_card_card_id_fkey FOREIGN KEY (card_id) REFERENCES public.card(card_id)
);
CREATE TABLE public.set (
  id text NOT NULL,
  set_name text NOT NULL,
  set_id text UNIQUE,
  set_label text UNIQUE,
  card_count smallint,
  set_publish_date timestamp without time zone,
  CONSTRAINT set_pkey PRIMARY KEY (id)
);
CREATE TABLE public.user (
  user_id text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  user_name text NOT NULL UNIQUE,
  CONSTRAINT user_pkey PRIMARY KEY (user_id)
);