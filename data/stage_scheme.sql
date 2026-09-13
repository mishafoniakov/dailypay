CREATE TABLE IF NOT EXISTS stage.expense (
    txn_date    date NOT NULL,
    payee_id       int,
    category_id    int,
    envelope_id    int,
    amount      numeric(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS stage.income (
    txn_date    date NOT NULL,
    payee_id       int,
    category_id    int,
    envelope_id    int,
    amount      numeric(12, 2) NOT NULL
);



CREATE TABLE IF NOT EXISTS stage.spr_payee (
    payee_id    smallint,
    payee       varchar(50)
);

CREATE TABLE IF NOT EXISTS stage.spr_category (
    category_id    smallint,
    category       varchar(50)
);

CREATE TABLE IF NOT EXISTS stage.spr_envelope (
    envelope_id    smallint,
    envelope       varchar(50)
);