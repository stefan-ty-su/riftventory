


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";





SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."card" (
    "set_id" "text" NOT NULL,
    "card_number" smallint NOT NULL,
    "card_id" "text" NOT NULL,
    "public_code" "text" NOT NULL,
    "card_name" "text" NOT NULL,
    "attr_energy" smallint,
    "attr_power" smallint,
    "attr_might" smallint,
    "card_type" "text",
    "card_supertype" "text",
    "card_rarity" "text",
    "card_domain" "text"[],
    "text_rich" "text",
    "text_plain" "text",
    "card_image_url" "text",
    "card_artist" "text",
    "card_tags" "text"[],
    "orientation" "text",
    "alternate_art" boolean DEFAULT false,
    "overnumbered" boolean DEFAULT false,
    "signature" boolean DEFAULT false
);


ALTER TABLE "public"."card" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."inventory" (
    "inventory_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "inventory_name" "text" DEFAULT 'My Inventory'::"text",
    "inventory_colour" "text",
    "created_at" timestamp with time zone,
    "last_updated" timestamp with time zone
);


ALTER TABLE "public"."inventory" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."inventory_card" (
    "inventory_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "card_id" "text" NOT NULL,
    "quantity" smallint DEFAULT '0'::smallint,
    "is_tradeable" boolean DEFAULT false,
    "locked_quantity" smallint DEFAULT '0'::smallint
);


ALTER TABLE "public"."inventory_card" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."set" (
    "id" "text" NOT NULL,
    "set_name" "text" NOT NULL,
    "set_id" "text",
    "set_label" "text",
    "card_count" smallint,
    "set_publish_date" timestamp without time zone
);


ALTER TABLE "public"."set" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trade" (
    "trade_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "initiator_user_id" "text" NOT NULL,
    "initiator_inventory_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "recipient_user_id" "text" NOT NULL,
    "recipient_inventory_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "status" "text" NOT NULL,
    "message" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "counter_count" smallint DEFAULT '0'::smallint NOT NULL,
    "initiator_confirmed" boolean DEFAULT false NOT NULL,
    "initiator_confirmed_at" timestamp with time zone,
    "parent_trade_id" "uuid" DEFAULT NULL,
    "recipient_confirmed" boolean DEFAULT false NOT NULL,
    "recipient_confirmed_at" timestamp with time zone,
    "resolved_at" timestamp with time zone,
    "root_trade_id" "uuid" DEFAULT "gen_random_uuid"()
);


ALTER TABLE "public"."trade" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trade_escrow" (
    "trade_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "card_id" "text" NOT NULL,
    "quantity" smallint
);


ALTER TABLE "public"."trade_escrow" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trade_history" (
    "history_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trade_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "root_trade_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "sequence_number" smallint NOT NULL,
    "actor_user_id" "text" NOT NULL,
    "action" "text" NOT NULL,
    "details" "jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."trade_history" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trade_recipient" (
    "trade_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "card_id" "text" NOT NULL,
    "quantity" smallint
);


ALTER TABLE "public"."trade_recipient" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user" (
    "user_id" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "user_name" "text" NOT NULL
);


ALTER TABLE "public"."user" OWNER TO "postgres";


ALTER TABLE ONLY "public"."card"
    ADD CONSTRAINT "card_pkey" PRIMARY KEY ("card_id");



ALTER TABLE ONLY "public"."card"
    ADD CONSTRAINT "card_public_code_key" UNIQUE ("public_code");



ALTER TABLE ONLY "public"."inventory_card"
    ADD CONSTRAINT "inventory_card_pkey" PRIMARY KEY ("inventory_id", "card_id");



ALTER TABLE ONLY "public"."inventory"
    ADD CONSTRAINT "inventory_pkey" PRIMARY KEY ("inventory_id");



ALTER TABLE ONLY "public"."set"
    ADD CONSTRAINT "set_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."set"
    ADD CONSTRAINT "set_set_id_key" UNIQUE ("set_id");



ALTER TABLE ONLY "public"."set"
    ADD CONSTRAINT "set_set_label_key" UNIQUE ("set_label");



ALTER TABLE ONLY "public"."trade_escrow"
    ADD CONSTRAINT "trade_escrow_pkey" PRIMARY KEY ("trade_id", "card_id");



ALTER TABLE ONLY "public"."trade_history"
    ADD CONSTRAINT "trade_history_pkey" PRIMARY KEY ("history_id");



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_pkey" PRIMARY KEY ("trade_id");



ALTER TABLE ONLY "public"."trade_recipient"
    ADD CONSTRAINT "trade_recipient_pkey" PRIMARY KEY ("trade_id", "card_id");



ALTER TABLE ONLY "public"."user"
    ADD CONSTRAINT "user_pkey" PRIMARY KEY ("user_id");



ALTER TABLE ONLY "public"."user"
    ADD CONSTRAINT "user_user_name_key" UNIQUE ("user_name");



ALTER TABLE ONLY "public"."card"
    ADD CONSTRAINT "card_set_id_fkey" FOREIGN KEY ("set_id") REFERENCES "public"."set"("set_id");



ALTER TABLE ONLY "public"."inventory_card"
    ADD CONSTRAINT "inventory_card_card_id_fkey" FOREIGN KEY ("card_id") REFERENCES "public"."card"("card_id") ON UPDATE CASCADE;



ALTER TABLE ONLY "public"."inventory_card"
    ADD CONSTRAINT "inventory_card_inventory_id_fkey" FOREIGN KEY ("inventory_id") REFERENCES "public"."inventory"("inventory_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."inventory"
    ADD CONSTRAINT "inventory_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("user_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade_escrow"
    ADD CONSTRAINT "trade_escrow_card_id_fkey" FOREIGN KEY ("card_id") REFERENCES "public"."card"("card_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade_escrow"
    ADD CONSTRAINT "trade_escrow_trade_id_fkey" FOREIGN KEY ("trade_id") REFERENCES "public"."trade"("trade_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade_history"
    ADD CONSTRAINT "trade_history_actor_user_id_fkey" FOREIGN KEY ("actor_user_id") REFERENCES "public"."user"("user_id");



ALTER TABLE ONLY "public"."trade_history"
    ADD CONSTRAINT "trade_history_root_trade_id_fkey" FOREIGN KEY ("root_trade_id") REFERENCES "public"."trade"("trade_id");



ALTER TABLE ONLY "public"."trade_history"
    ADD CONSTRAINT "trade_history_trade_id_fkey" FOREIGN KEY ("trade_id") REFERENCES "public"."trade"("trade_id");



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_initiator_inventory_id_fkey" FOREIGN KEY ("initiator_inventory_id") REFERENCES "public"."inventory"("inventory_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_initiator_user_id_fkey" FOREIGN KEY ("initiator_user_id") REFERENCES "public"."user"("user_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_parent_trade_id_fkey" FOREIGN KEY ("parent_trade_id") REFERENCES "public"."trade"("trade_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade_recipient"
    ADD CONSTRAINT "trade_recipient_card_id_fkey" FOREIGN KEY ("card_id") REFERENCES "public"."card"("card_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_recipient_inventory_id_fkey" FOREIGN KEY ("recipient_inventory_id") REFERENCES "public"."inventory"("inventory_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade_recipient"
    ADD CONSTRAINT "trade_recipient_trade_id_fkey" FOREIGN KEY ("trade_id") REFERENCES "public"."trade"("trade_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_recipient_user_id_fkey" FOREIGN KEY ("recipient_user_id") REFERENCES "public"."user"("user_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trade"
    ADD CONSTRAINT "trade_root_trade_id_fkey" FOREIGN KEY ("root_trade_id") REFERENCES "public"."trade"("trade_id") ON DELETE CASCADE;



ALTER TABLE "public"."card" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."inventory" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."inventory_card" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."set" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trade" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trade_escrow" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trade_history" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trade_recipient" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";








































































































































































GRANT ALL ON TABLE "public"."card" TO "anon";
GRANT ALL ON TABLE "public"."card" TO "authenticated";
GRANT ALL ON TABLE "public"."card" TO "service_role";



GRANT ALL ON TABLE "public"."inventory" TO "anon";
GRANT ALL ON TABLE "public"."inventory" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory" TO "service_role";



GRANT ALL ON TABLE "public"."inventory_card" TO "anon";
GRANT ALL ON TABLE "public"."inventory_card" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory_card" TO "service_role";



GRANT ALL ON TABLE "public"."set" TO "anon";
GRANT ALL ON TABLE "public"."set" TO "authenticated";
GRANT ALL ON TABLE "public"."set" TO "service_role";



GRANT ALL ON TABLE "public"."trade" TO "anon";
GRANT ALL ON TABLE "public"."trade" TO "authenticated";
GRANT ALL ON TABLE "public"."trade" TO "service_role";



GRANT ALL ON TABLE "public"."trade_escrow" TO "anon";
GRANT ALL ON TABLE "public"."trade_escrow" TO "authenticated";
GRANT ALL ON TABLE "public"."trade_escrow" TO "service_role";



GRANT ALL ON TABLE "public"."trade_history" TO "anon";
GRANT ALL ON TABLE "public"."trade_history" TO "authenticated";
GRANT ALL ON TABLE "public"."trade_history" TO "service_role";



GRANT ALL ON TABLE "public"."trade_recipient" TO "anon";
GRANT ALL ON TABLE "public"."trade_recipient" TO "authenticated";
GRANT ALL ON TABLE "public"."trade_recipient" TO "service_role";



GRANT ALL ON TABLE "public"."user" TO "anon";
GRANT ALL ON TABLE "public"."user" TO "authenticated";
GRANT ALL ON TABLE "public"."user" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































