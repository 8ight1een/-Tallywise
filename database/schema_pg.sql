CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name_accounts TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, name_accounts)
);

CREATE TABLE categories (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name_categories TEXT NOT NULL,
    money_type TEXT NOT NULL CHECK (money_type IN ('收入', '支出')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, name_categories)
);

CREATE TABLE transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    category_id INT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    money NUMERIC(12, 2) NOT NULL,
    money_type TEXT NOT NULL CHECK (money_type IN ('收入', '支出')),
    CHECK (
        (money_type = '收入' AND money > 0)
        OR
        (money_type = '支出' AND money < 0)
    ),
    description TEXT,
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trans_user_date ON transactions (user_id, transaction_date);

CREATE INDEX idx_trans_user_account ON transactions (user_id, account_id);

CREATE INDEX idx_trans_user_category ON transactions (user_id, category_id);