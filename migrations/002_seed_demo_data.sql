INSERT INTO companies (name, contact_name, email, phone)
SELECT seed.name, seed.contact_name, seed.email, seed.phone
FROM (VALUES
    ('株式会社ABC', '山田 太郎', 'yamada@abc.example.jp', '03-1234-5678'),
    ('株式会社XYZ', '佐藤 花子', 'sato@xyz.example.jp', '06-2345-6789'),
    ('合同会社みどり', '鈴木 一郎', 'suzuki@midori.example.jp', '052-345-6789'),
    ('株式会社サンプル', NULL, NULL, NULL),
    ('有限会社つばき', '高橋 美咲', 'takahashi@tsubaki.example.jp', '092-456-7890')
) AS seed(name, contact_name, email, phone)
WHERE NOT EXISTS (
    SELECT 1
    FROM companies
    WHERE companies.name = seed.name
);

INSERT INTO bento (name, price)
SELECT seed.name, seed.price
FROM (VALUES
    ('唐揚げ弁当', 800),
    ('鮭弁当', 850),
    ('幕の内弁当', 1000),
    ('ハンバーグ弁当', 900),
    ('野菜弁当', 780)
) AS seed(name, price)
WHERE NOT EXISTS (
    SELECT 1
    FROM bento
    WHERE bento.name = seed.name
);

INSERT INTO allergens (name) VALUES
    ('小麦'), ('卵'), ('乳'), ('えび'),
    ('かに'), ('そば'), ('落花生'), ('大豆')
ON CONFLICT (name) DO NOTHING;

INSERT INTO bento_allergens (bento_id, allergen_id)
SELECT b.id, a.id
FROM (VALUES
    ('唐揚げ弁当', '小麦'), ('唐揚げ弁当', '卵'), ('唐揚げ弁当', '大豆'),
    ('鮭弁当', '小麦'), ('鮭弁当', '大豆'),
    ('幕の内弁当', '小麦'), ('幕の内弁当', '卵'),
    ('幕の内弁当', '乳'), ('幕の内弁当', '大豆'),
    ('ハンバーグ弁当', '小麦'), ('ハンバーグ弁当', '卵'),
    ('ハンバーグ弁当', '乳'), ('ハンバーグ弁当', '大豆'),
    ('野菜弁当', '大豆')
) AS seed(bento_name, allergen_name)
JOIN bento AS b ON b.name = seed.bento_name
JOIN allergens AS a ON a.name = seed.allergen_name
ON CONFLICT (bento_id, allergen_id) DO NOTHING;

WITH order_lines(company_name, order_date, bento_name, quantity) AS (
    VALUES
        ('株式会社ABC', DATE '2026-09-22', '唐揚げ弁当', 10),
        ('株式会社ABC', DATE '2026-09-22', '鮭弁当', 5),
        ('株式会社XYZ', DATE '2026-09-24', '幕の内弁当', 8),
        ('株式会社XYZ', DATE '2026-09-24', '野菜弁当', 4),
        ('合同会社みどり', DATE '2026-09-26', '鮭弁当', 6),
        ('合同会社みどり', DATE '2026-09-26', 'ハンバーグ弁当', 3)
), new_orders AS (
    INSERT INTO orders (company_id, order_date)
    SELECT c.id, seed.order_date
    FROM (
        SELECT DISTINCT company_name, order_date
        FROM order_lines
    ) AS seed
    JOIN companies AS c ON c.name = seed.company_name
    WHERE NOT EXISTS (
        SELECT 1
        FROM orders AS existing
        WHERE existing.company_id = c.id
            AND existing.order_date = seed.order_date
    )
    RETURNING id, company_id, order_date
)
INSERT INTO order_items (order_id, bento_id, quantity)
SELECT new_orders.id, b.id, order_lines.quantity
FROM new_orders
JOIN companies AS c ON c.id = new_orders.company_id
JOIN order_lines
    ON order_lines.company_name = c.name
    AND order_lines.order_date = new_orders.order_date
JOIN bento AS b ON b.name = order_lines.bento_name
ON CONFLICT (order_id, bento_id) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES ('002_seed_demo_data.sql');