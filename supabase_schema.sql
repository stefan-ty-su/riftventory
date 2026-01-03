-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.card (
  id text NOT NULL,
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
  CONSTRAINT card_pkey PRIMARY KEY (id),
  CONSTRAINT card_set_id_fkey FOREIGN KEY (set_id) REFERENCES public.set(set_id)
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