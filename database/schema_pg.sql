CREATE TABLE users (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(250) NOT NULL,
    nickname VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,
    name_accounts VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,
    name_categories VARCHAR(100) NOT NULL,
    money_type VARCHAR(10) NOT NULL
        CHECK (money_type IN ('收入', '支出')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, name_categories)
);

CREATE TABLE transactions (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,
    account_id INT NOT NULL
        REFERENCES accounts(id) ON DELETE RESTRICT,
    category_id INT NOT NULL
        REFERENCES categories(id) ON DELETE RESTRICT,

    money NUMERIC(9, 2) NOT NULL CHECK (money > 0),
    money_type VARCHAR(10) NOT NULL
        CHECK (money_type IN ('收入', '支出')),

    description VARCHAR(250),
    transaction_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_accounts_user
    ON accounts (user_id);

CREATE INDEX idx_trans_user_date
    ON transactions (user_id, transaction_date);

CREATE INDEX idx_trans_account
    ON transactions (account_id);

CREATE INDEX idx_trans_category
    ON transactions (category_id);
