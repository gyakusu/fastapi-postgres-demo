CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50)
);

CREATE TABLE bento (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0)
);

CREATE TABLE allergens (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies (id),
    order_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
    order_id BIGINT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    bento_id BIGINT NOT NULL REFERENCES bento (id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, bento_id)
);

CREATE TABLE bento_allergens (
    bento_id BIGINT NOT NULL REFERENCES bento (id) ON DELETE CASCADE,
    allergen_id BIGINT NOT NULL REFERENCES allergens (id) ON DELETE CASCADE,
    PRIMARY KEY (bento_id, allergen_id)
);

INSERT INTO schema_migrations (version) VALUES ('001_create_schema.sql');