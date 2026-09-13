CREATE TABLE IF NOT EXISTS raw.expense (
    txn_date    date NOT NULL,
    payee       text,
    category    text,
    description text,
    envelope    text,
    amount      numeric(12, 2) NOT NULL,
    source_file text NOT NULL,
    loaded_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE raw.expense DROP CONSTRAINT IF EXISTS expense_pkey;
ALTER TABLE raw.expense ADD PRIMARY KEY (txn_date, category, envelope, amount);

CREATE TABLE IF NOT EXISTS raw.income (
    txn_date    date NOT NULL,
    payee       text,
    category    text,
    description text,
    envelope    text,
    amount      numeric(12, 2) NOT NULL,
    source_file text NOT NULL,
    loaded_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE raw.income DROP CONSTRAINT IF EXISTS income_pkey;
ALTER TABLE raw.income ADD PRIMARY KEY (txn_date, category, envelope, amount);
