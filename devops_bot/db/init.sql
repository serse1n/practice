CREATE USER repl_user WITH REPLICATION PASSWORD '1234';

SELECT pg_create_physical_replication_slot('replication_slot');

CREATE TABLE IF NOT EXISTS emails (
        id SERIAL PRIMARY KEY,
        email VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS phones (
        id SERIAL PRIMARY KEY,
        phone VARCHAR(20) NOT NULL
);

INSERT INTO emails (email)
VALUES ('test@ptsecurity.com');

INSERT INTO phones (phone)
VALUES ('89684236778');
