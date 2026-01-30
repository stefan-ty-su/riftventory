-- Migration: Change user_id from TEXT to UUID (with data conversion)
-- This migration converts all user_id columns from TEXT to UUID type
-- while preserving existing data by generating new UUIDs and updating references

-- Step 1: Add temporary UUID columns
ALTER TABLE "public"."user" ADD COLUMN "new_user_id" uuid DEFAULT gen_random_uuid();
ALTER TABLE "public"."inventory" ADD COLUMN "new_user_id" uuid;
ALTER TABLE "public"."trade" ADD COLUMN "new_initiator_user_id" uuid;
ALTER TABLE "public"."trade" ADD COLUMN "new_recipient_user_id" uuid;
ALTER TABLE "public"."trade_history" ADD COLUMN "new_actor_user_id" uuid;

-- Step 2: Populate new UUID columns based on mapping from user table
UPDATE "public"."inventory" i
SET "new_user_id" = u."new_user_id"
FROM "public"."user" u
WHERE i."user_id" = u."user_id";

UPDATE "public"."trade" t
SET "new_initiator_user_id" = u."new_user_id"
FROM "public"."user" u
WHERE t."initiator_user_id" = u."user_id";

UPDATE "public"."trade" t
SET "new_recipient_user_id" = u."new_user_id"
FROM "public"."user" u
WHERE t."recipient_user_id" = u."user_id";

UPDATE "public"."trade_history" th
SET "new_actor_user_id" = u."new_user_id"
FROM "public"."user" u
WHERE th."actor_user_id" = u."user_id";

-- Step 3: Drop old constraints
ALTER TABLE "public"."inventory" DROP CONSTRAINT IF EXISTS "inventory_user_id_fkey";
ALTER TABLE "public"."trade" DROP CONSTRAINT IF EXISTS "trade_initiator_user_id_fkey";
ALTER TABLE "public"."trade" DROP CONSTRAINT IF EXISTS "trade_recipient_user_id_fkey";
ALTER TABLE "public"."trade_history" DROP CONSTRAINT IF EXISTS "trade_history_actor_user_id_fkey";
ALTER TABLE "public"."user" DROP CONSTRAINT IF EXISTS "user_pkey";

-- Step 4: Drop old columns and rename new ones
ALTER TABLE "public"."user" DROP COLUMN "user_id";
ALTER TABLE "public"."user" RENAME COLUMN "new_user_id" TO "user_id";

ALTER TABLE "public"."inventory" DROP COLUMN "user_id";
ALTER TABLE "public"."inventory" RENAME COLUMN "new_user_id" TO "user_id";

ALTER TABLE "public"."trade" DROP COLUMN "initiator_user_id";
ALTER TABLE "public"."trade" RENAME COLUMN "new_initiator_user_id" TO "initiator_user_id";

ALTER TABLE "public"."trade" DROP COLUMN "recipient_user_id";
ALTER TABLE "public"."trade" RENAME COLUMN "new_recipient_user_id" TO "recipient_user_id";

ALTER TABLE "public"."trade_history" DROP COLUMN "actor_user_id";
ALTER TABLE "public"."trade_history" RENAME COLUMN "new_actor_user_id" TO "actor_user_id";

-- Step 5: Re-add constraints
ALTER TABLE "public"."user" ADD CONSTRAINT "user_pkey" PRIMARY KEY ("user_id");

ALTER TABLE "public"."inventory"
    ADD CONSTRAINT "inventory_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."user"("user_id") ON DELETE CASCADE;

ALTER TABLE "public"."trade"
    ADD CONSTRAINT "trade_initiator_user_id_fkey"
    FOREIGN KEY ("initiator_user_id") REFERENCES "public"."user"("user_id") ON DELETE CASCADE;

ALTER TABLE "public"."trade"
    ADD CONSTRAINT "trade_recipient_user_id_fkey"
    FOREIGN KEY ("recipient_user_id") REFERENCES "public"."user"("user_id") ON DELETE CASCADE;

ALTER TABLE "public"."trade_history"
    ADD CONSTRAINT "trade_history_actor_user_id_fkey"
    FOREIGN KEY ("actor_user_id") REFERENCES "public"."user"("user_id");
