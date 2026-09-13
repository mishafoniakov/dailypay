ALTER TABLE raw.expense DROP CONSTRAINT IF EXISTS expense_pkey;
ALTER TABLE raw.expense ADD PRIMARY KEY (txn_date, category, envelope, amount);

ALTER TABLE raw.income DROP CONSTRAINT IF EXISTS income_pkey;
ALTER TABLE raw.income ADD PRIMARY KEY (txn_date, category, envelope, amount);

ALTER TABLE stage.spr_payee DROP CONSTRAINT IF EXISTS spr_payee_pkey;
ALTER TABLE stage.spr_payee ADD PRIMARY KEY (payee_id);

ALTER TABLE stage.spr_category DROP CONSTRAINT IF EXISTS spr_category_pkey;
ALTER TABLE stage.spr_category ADD PRIMARY KEY (category_id);

ALTER TABLE stage.spr_envelope DROP CONSTRAINT IF EXISTS spr_envelope_pkey;
ALTER TABLE stage.spr_envelope ADD PRIMARY KEY (envelope_id);