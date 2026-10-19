"""Align primary keys with the existing GENERATED ALWAYS identity schema."""
from alembic import op


revision = "b27f4e9a6c10"
down_revision = "5e649e7423b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        LOCK TABLE public.users, public.accounts, public.categories, public.transactions
        IN ACCESS EXCLUSIVE MODE;
        DO $$
        DECLARE
            table_name text;
            target regclass;
            identity_kind text;
            old_sequence regclass;
            sequence_value bigint;
            sequence_called boolean;
            next_id bigint;
            maximum_id bigint;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY['users', 'accounts', 'categories', 'transactions'] LOOP
                target := format('public.%I', table_name)::regclass;
                SELECT attidentity::text INTO identity_kind FROM pg_attribute
                WHERE attrelid = target AND attname = 'id' AND NOT attisdropped;
                IF identity_kind = 'a' THEN
                    CONTINUE;
                ELSIF identity_kind = 'd' THEN
                    EXECUTE format('ALTER TABLE %s ALTER COLUMN id SET GENERATED ALWAYS', target);
                    CONTINUE;
                END IF;
                old_sequence := pg_get_serial_sequence(target::text, 'id')::regclass;
                IF old_sequence IS NULL OR
                   (SELECT seqincrement FROM pg_sequence WHERE seqrelid = old_sequence) <> 1 THEN
                    RAISE EXCEPTION 'Expected an owned sequence with increment 1 for %.id', target;
                END IF;
                EXECUTE format('SELECT last_value, is_called FROM %s', old_sequence)
                    INTO sequence_value, sequence_called;
                EXECUTE format('SELECT max(id) FROM %s', target) INTO maximum_id;
                next_id := greatest(sequence_value + CASE WHEN sequence_called THEN 1 ELSE 0 END,
                                    coalesce(maximum_id, 0) + 1, 1);
                EXECUTE format('ALTER TABLE %s ALTER COLUMN id DROP DEFAULT', target);
                EXECUTE format('ALTER SEQUENCE %s OWNED BY NONE', old_sequence);
                EXECUTE format('DROP SEQUENCE %s', old_sequence);
                EXECUTE format('ALTER TABLE %s ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY', target);
                PERFORM setval(pg_get_serial_sequence(target::text, 'id')::regclass, next_id, false);
            END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        LOCK TABLE public.users, public.accounts, public.categories, public.transactions
        IN ACCESS EXCLUSIVE MODE;
        DO $$
        DECLARE
            table_name text;
            target regclass;
            identity_kind text;
            old_sequence regclass;
            sequence_name text;
            sequence_value bigint;
            sequence_called boolean;
            next_id bigint;
            maximum_id bigint;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY['users', 'accounts', 'categories', 'transactions'] LOOP
                target := format('public.%I', table_name)::regclass;
                SELECT attidentity::text INTO identity_kind FROM pg_attribute
                WHERE attrelid = target AND attname = 'id' AND NOT attisdropped;
                IF identity_kind = '' THEN
                    CONTINUE;
                END IF;
                old_sequence := pg_get_serial_sequence(target::text, 'id')::regclass;
                IF (SELECT seqincrement FROM pg_sequence WHERE seqrelid = old_sequence) <> 1 THEN
                    RAISE EXCEPTION 'Expected an identity sequence with increment 1 for %.id', target;
                END IF;
                EXECUTE format('SELECT last_value, is_called FROM %s', old_sequence)
                    INTO sequence_value, sequence_called;
                EXECUTE format('SELECT max(id) FROM %s', target) INTO maximum_id;
                next_id := greatest(sequence_value + CASE WHEN sequence_called THEN 1 ELSE 0 END,
                                    coalesce(maximum_id, 0) + 1, 1);
                sequence_name := format('public.%I', table_name || '_id_seq');
                EXECUTE format('ALTER TABLE %s ALTER COLUMN id DROP IDENTITY', target);
                EXECUTE format('CREATE SEQUENCE %s AS integer', sequence_name);
                EXECUTE format('ALTER SEQUENCE %s OWNED BY %s.id', sequence_name, target);
                EXECUTE format('ALTER TABLE %s ALTER COLUMN id SET DEFAULT nextval(%L::regclass)', target, sequence_name);
                PERFORM setval(sequence_name::regclass, next_id, false);
            END LOOP;
        END $$;
    """)
