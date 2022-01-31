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

--
-- Name: api; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA api;


--
-- Name: internal; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA internal;


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: sanctions; Type: TABLE; Schema: internal; Owner: -
--

CREATE TABLE internal.sanctions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    target_type text NOT NULL,
    source text NOT NULL,
    source_id text NOT NULL,
    names text[] DEFAULT '{}'::text[],
    positions text[] DEFAULT '{}'::text[],
    remarks text,
    listed_on date,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT sanctions_source_check CHECK ((source = ANY (ARRAY['ofac'::text, 'unsc'::text, 'eu'::text]))),
    CONSTRAINT sanctions_target_type_check CHECK ((target_type = ANY (ARRAY['individual'::text, 'entity'::text, 'aircraft'::text, 'vessel'::text])))
);


--
-- Name: sanctions; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.sanctions AS
 SELECT sanctions.id,
    sanctions.target_type,
    sanctions.source,
    sanctions.source_id,
    sanctions.names,
    sanctions.positions,
    sanctions.remarks,
    sanctions.listed_on,
    sanctions.created_at
   FROM internal.sanctions;


--
-- Name: search_sanctions(text); Type: FUNCTION; Schema: api; Owner: -
--

CREATE FUNCTION api.search_sanctions(name text) RETURNS SETOF api.sanctions
    LANGUAGE sql STABLE
    AS $$
  select * from api.sanctions
  where name % any(names);
$$;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying(255) NOT NULL
);


--
-- Name: sanctions sanctions_pkey; Type: CONSTRAINT; Schema: internal; Owner: -
--

ALTER TABLE ONLY internal.sanctions
    ADD CONSTRAINT sanctions_pkey PRIMARY KEY (id);


--
-- Name: sanctions sanctions_source_source_id_key; Type: CONSTRAINT; Schema: internal; Owner: -
--

ALTER TABLE ONLY internal.sanctions
    ADD CONSTRAINT sanctions_source_source_id_key UNIQUE (source, source_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- PostgreSQL database dump complete
--


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20220128221810');
