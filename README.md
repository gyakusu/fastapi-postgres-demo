# FastAPI PostgreSQL Demo

弁当の仕出し注文を題材にした、業務用デモアプリです。

**FastAPI + PostgreSQL + HTML/Jinja2** というシンプルな構成で、RDBにおける1対多・多対多の関係と、Webアプリケーションからのデータ登録・取得を確認することを目的とします。

現在の実装では、**会社を選択して弁当を数量指定し、注文を登録する**ところまでを一連の画面として実装しています。また、登録した注文の履歴と、個別の注文完了画面も提供しています。

---

## 1. システム構成

```mermaid
flowchart LR
    B[Browser]
    F[FastAPI]
    P[(PostgreSQL)]

    B -->|HTTP GET / POST| F
    F -->|SQL| P
```

使用技術：

- Python
- FastAPI
- Uvicorn
- psycopg
- PostgreSQL
- Pydantic
- Jinja2

フロントエンドは**HTML/Jinja2を中心としたシンプルな構成**です。

ReactやVueなどのフロントエンドフレームワークは使用していません。

---

## 2. PostgreSQL

デフォルトの接続先は `demo_db` です。

`db.py` では、環境変数 `DATABASE_URL` が設定されている場合はそれを使用し、設定されていない場合は以下を使用します。

```text
dbname=demo_db
```

接続確認：

```bash
psql demo_db
```

本番環境などでは、例えば `DATABASE_URL` を設定して接続先を切り替えられます。

---

## 3. ディレクトリ構成

現在のPythonコードから確認できるアプリケーション構成は次のとおりです。

```text
fastapi-postgres-demo/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── schemas.py
│   └── templates/
│       ├── index.html
│       ├── order_history.html
│       └── order_complete.html
├── .venv/
├── .gitignore
└── ...
```

`main.py` では `app/templates` をJinja2のテンプレートディレクトリとして使用しています。

---

## 4. データベーススキーマ

現在のアプリケーションで利用している主要なテーブルは以下です。

```mermaid
erDiagram
    companies ||--o{ orders : places
    orders ||--o{ order_items : contains
    bento ||--o{ order_items : ordered
    bento ||--o{ bento_allergens : has
    allergens ||--o{ bento_allergens : applies

    companies {
        bigint id PK
        varchar name
        varchar contact_name
        varchar email
        varchar phone
    }
    orders {
        bigint id PK
        bigint company_id FK
        date order_date
        timestamp created_at
    }

    order_items {
        bigint order_id PK,FK
        bigint bento_id PK,FK
        integer quantity
    }

    bento {
        bigint id PK
        varchar name
        integer price
    }

    allergens {
        bigint id PK
        varchar name
    }
    bento_allergens {
        bigint bento_id PK,FK
        bigint allergen_id PK,FK
    }
```

### 4.1 `companies`

注文元の会社を管理します。

| Column | Type | Constraint | Description |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 会社ID |
| `name` | VARCHAR(200) | NOT NULL | 会社名 |
| `contact_name` | VARCHAR(100) | | 担当者名 |
| `email` | VARCHAR(255) | | メールアドレス |
| `phone` | VARCHAR(50) | | 電話番号 |

現在のPythonコードでは、注文画面に表示するために `id` と `name` を取得しています。

```sql
SELECT id, name
FROM companies
ORDER BY name;
```

`contact_name`、`email`、`phone` はスキーマとして保持されていますが、現在の注文処理では使用していません。
---

### 4.2 `orders`

1回の注文を管理します。

| Column | Type | Constraint | Description |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 注文ID |
| `company_id` | BIGINT | FK | 注文元会社 |
| `order_date` | DATE | NOT NULL | 注文日 |
| `created_at` | TIMESTAMP | NOT NULL | 登録日時 |

関係：

```mermaid
flowchart LR
    C[companies] -->|1 : N| O[orders]
```

1つの会社から複数の注文が発生します。

注文登録時には、`company_id`、`order_date`、`created_at` が登録されます。

`created_at` はSQL側で `NOW()` を使用して設定します。

---

### 4.3 `bento`

弁当マスタです。

| Column | Type | Constraint | Description |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 弁当ID |
| `name` | VARCHAR(200) | NOT NULL | 弁当名 |
| `price` | INTEGER | NOT NULL | 価格 |

現在のPythonコードでは、注文画面に表示するために `id`、`name`、`price` を取得しています。

```sql
SELECT id, name, price
FROM bento
ORDER BY id;
```

価格は注文履歴・注文詳細画面の合計金額計算にも使用されます。

---

### 4.4 `order_items`

1つの注文に含まれる弁当と数量を管理します。

| Column | Type | Constraint | Description |
|---|---|---|---|
| `order_id` | BIGINT | PK, FK | 注文ID |
| `bento_id` | BIGINT | PK, FK | 弁当ID |
| `quantity` | INTEGER | NOT NULL | 数量 |

複合主キー：

```text
PRIMARY KEY (order_id, bento_id)
```

関係：

```mermaid
flowchart LR
    O[orders] -->|N : N| B[bento]
    O --> OI[order_items]
    B --> OI
```

例えば、1つの注文に複数種類の弁当を含めることができます。

```text
注文ID 1
  ├── 唐揚げ弁当 × 10
  ├── 鮭弁当     × 5
  └── 幕の内弁当 × 3
```

注文登録時には、`orders` に注文ヘッダを登録した後、`order_items` に各弁当の数量を登録します。

---

### 4.5 `allergens`

アレルギー情報のマスタです。

| Column | Type | Constraint | Description |
|---|---|---|---|
| `id` | BIGSERIAL | PK | アレルギーID |
| `name` | VARCHAR(100) | NOT NULL, UNIQUE | アレルギー名 |

注文画面の食品アレルギー表で、弁当に含まれるアレルゲンの表示に利用しています。

---

### 4.6 `bento_allergens`

弁当とアレルギーの多対多関係を管理します。

| Column | Type | Constraint | Description |
|---|---|---|---|
| `bento_id` | BIGINT | PK, FK | 弁当ID |
| `allergen_id` | BIGINT | PK, FK | アレルギーID |

関係：

```mermaid
flowchart LR
    B[bento] -->|N : N| A[allergens]
    B --> BA[bento_allergens]
    A --> BA
```

例えば、次のような関係を表現できます。

```text
唐揚げ弁当
  ├── 小麦
  ├── 卵
  └── 大豆
```

注文画面の食品アレルギー表で、弁当とアレルギーの関係を取得するために利用しています。

---

## 5. アプリケーションのデータモデル

Python側では、Pydanticを利用してデータモデルを定義しています。

モデルは `frozen=True` としており、生成後に変更できないイミュータブルなモデルとして扱います。

### `Company`

```text
id: int
name: str
```

### `Bento`

```text
id: int
name: str
price: int
```

`price` は0以上です。

### `OrderSummary`

```text
id: int
order_date: str
company_name: str
total_price: int
```

注文履歴・注文完了画面で使用する注文の概要です。

### `OrderItem`

```text
name: str
quantity: int
price: int
subtotal: int
```

注文に含まれる弁当1種類分の明細です。

### `QuantitySelection`

```text
bento_id: int
quantity: int
```

フォームから受け取った「弁当IDと数量」の組を表します。

### `OrderDraft`

```text
company_id: int
order_date: str
quantities: tuple[QuantitySelection, ...]
```

注文登録前のデータを表します。

---

# 6. API / Route

現在のFastAPIアプリケーションでは、以下のRouteを提供しています。

| Method | Path | 内容 |
|---|---|---|
| GET | `/` | 注文登録画面 |
| POST | `/orders` | 注文登録 |
| GET | `/orders` | 注文履歴 |
| GET | `/orders/complete` | 注文完了・注文詳細 |

---

## 6.1 GET `/`

注文登録画面を表示します。

```http
GET /
```

FastAPIからテンプレートへ以下のデータを渡します。

```text
companies
bentos
```

`companies` は会社選択欄、`bentos` は弁当と価格・数量入力欄の生成に利用します。

---

## 6.2 POST `/orders`

注文を登録します。

```http
POST /orders
Content-Type: application/x-www-form-urlencoded
```

注文には、

- 注文元会社
- 注文日
- 1種類以上の弁当
- 各弁当の数量

が必要です。

### フォーム項目

```text
company_id
order_date
quantity_{bento.id}
```

例えば、

```text
company_id=1
order_date=2026-08-30
quantity_1=10
quantity_2=5
quantity_3=3
```

のようなフォームを受け取ります。

`quantity_N` の `N` は `bento.id` を表します。

FastAPI側では、`quantity_` を取り除いた文字列を整数に変換して弁当IDとして扱います。

数量が0以下の項目は注文対象から除外され、1つも正の数量が存在しない場合は400エラーになります。

---

## 6.3 注文登録の処理

注文登録は、注文ヘッダと注文明細を**同一トランザクション**で処理します。

```mermaid
flowchart TD
    A[POST /orders] --> B[フォームを解析]
    B --> C[OrderDraftを生成]
    C --> D[INSERT orders]
    D --> E[order_idを取得]
    E --> F[INSERT order_items]
    F --> G[COMMIT]
    G --> H[303 Redirect]
    H --> I[/orders/complete?order_id=...]
```

`db.insert_order()` では、

1. `orders` に注文を登録
2. `RETURNING id` で注文IDを取得
3. `order_items` に各明細を登録
4. すべて成功したらコミット

という流れで処理します。

途中でエラーが発生した場合はトランザクション全体がロールバックされます。

したがって、

```text
orders
```

だけ登録されて、

```text
order_items
```

が登録されない状態を避ける設計になっています。

---

## 6.4 GET `/orders`

注文履歴を表示します。

```http
GET /orders
```

注文ごとに、

- 注文ID
- 注文日
- 会社名
- 合計金額

を取得します。

合計金額は、以下の関係からSQLで計算しています。

```text
bento.price × order_items.quantity
```

複数の明細がある場合は `SUM()` で合計します。

注文は、

```text
注文日 DESC
注文ID DESC
```

の順で表示されます。

---

## 6.5 GET `/orders/complete`

注文登録後の注文完了画面、および個別注文の詳細を表示します。

```http
GET /orders/complete?order_id=1
```

注文IDに対応する、

- 注文ID
- 注文日
- 会社名
- 合計金額
- 弁当名
- 数量
- 単価
- 小計

を取得します。

存在しない注文IDが指定された場合は `404 Not Found` を返します。

---

# 7. 注文履歴のデータ取得

注文履歴では、`orders`、`companies`、`order_items`、`bento` をJOINして注文情報を取得します。

概念的には次のような関係です。

```mermaid
flowchart LR
    C[companies] --> O[orders]
    O --> OI[order_items]
    B[bento] --> OI
```

注文の合計金額は、

```sql
SUM(b.price * oi.quantity)
```

によって計算します。

注文詳細では、明細ごとに、

```sql
b.price * oi.quantity
```

を小計として取得します。

---

# 8. HTMLとDBの対応

注文登録画面では、HTMLのフォーム項目とデータベースの列を次のように対応させています。

| HTML | Python | PostgreSQL |
|---|---|---|
| 会社選択 | `company_id` | `companies.id` |
| 注文日 | `order_date` | `orders.order_date` |
| 弁当 | `bento.id` | `bento.id` |
| 弁当名 | `bento.name` | `bento.name` |
| 価格 | `bento.price` | `bento.price` |
| 数量 | `quantity_{bento.id}` | `order_items.quantity` |
| 注文 | `POST /orders` | `orders` |
| 注文明細 | `POST /orders` | `order_items` |

アレルギーについては、現在の画面・Python処理では未使用ですが、データベースには、

```text
allergens
bento_allergens
```

を含むスキーマを保持しています。

---

# 9. データベースアクセス

`app/db.py` がPostgreSQLへのアクセスを担当します。

主な関数：

| Function | 内容 |
|---|---|
| `get_connection()` | PostgreSQLへの接続を作成 |
| `fetch_companies()` | 会社一覧を取得 |
| `fetch_bentos()` | 弁当一覧を取得 |
| `fetch_bento_allergens()` | 弁当ごとのアレルゲン一覧を取得 |
| `fetch_orders()` | 注文履歴を取得 |
| `fetch_order(order_id)` | 注文と明細を取得 |
| `insert_order(draft)` | 注文と明細を登録 |

ORMは使用せず、SQLを明示的に記述しています。

データベースから取得した行は、`Company`、`Bento`、`OrderSummary`、`OrderItem` などのPydanticモデルへ変換します。

---

# 10. 起動

依存関係を同期：

```bash
uv sync
```

FastAPIを起動：

```bash
uv run uvicorn app.main:app --reload
```

ブラウザ：

```text
http://127.0.0.1:8000/
```

Swagger UI：

```text
http://127.0.0.1:8000/docs
```

なお、このアプリケーションの主要な画面はHTML/Jinja2による画面であり、Swagger UIはFastAPIが提供するAPIドキュメントです。

---

# 11. 現在のアプリケーション構成

現在の実装は、概ね次の構造になっています。

```mermaid
flowchart TD
    UI[Browser / Jinja2 HTML]
    API[FastAPI main.py]
    MODEL[Pydantic schemas.py]
    DBLAYER[PostgreSQL access db.py]
    DB[(PostgreSQL)]

    UI -->|GET /| API
    UI -->|POST /orders| API
    UI -->|GET /orders| API
    UI -->|GET /orders/complete| API

    API --> MODEL
    API --> DBLAYER
    DBLAYER --> DB
```

役割は次のように分かれています。

- `main.py`
  - HTTPリクエストを受け取る
  - フォームを解析する
  - Pydanticモデルを生成する
  - DB操作を呼び出す
  - Jinja2テンプレートを返す
- `schemas.py`
  - アプリケーションで扱うデータモデルを定義する
  - Pydanticによる値の制約を定義する
- `db.py`
  - PostgreSQLへの接続を行う
  - SQLを実行する
  - DBの行をPydanticモデルへ変換する

---

# 12. 設計上の方針

このデモでは、まず**理解しやすさを優先**します。

- ORMは使用しない
- SQLを明示的に記述する
- PostgreSQLの外部キーを利用する
- 多対多は中間テーブルで表現する
- 注文登録はトランザクションで処理する
- HTML/Jinja2を中心としたシンプルなフロントエンドにする
- 必要以上にフレームワークを導入しない
- Python側のデータモデルはイミュータブルに扱う

特に注文登録では、`OrderDraft` や `QuantitySelection` などのモデルを介して、フォームから受け取ったデータを明示的なデータ構造に変換してからDBへ渡します。

---

# 13. 現在実装されている機能

現在のPythonコードから確認できる範囲では、以下が実装済みです。

- 会社一覧の取得
- 弁当一覧の取得
- 弁当価格の表示
- メイン画面から開く食品アレルギー表
- 会社・注文日・弁当数量を指定した注文登録
- 注文と注文明細のトランザクション処理
- 注文履歴の表示
- 注文ごとの合計金額の計算
- 個別注文の完了・詳細画面
- 存在しない注文への404応答
- 金額の「円」形式での表示

一方、以下はデータベーススキーマには存在しますが、現在の注文処理では使用していません。

- `companies.contact_name`
- `companies.email`
- `companies.phone`

---

# 14. 今後の拡張候補

現在すでに注文登録・注文履歴・注文詳細まで実装されているため、今後の拡張候補は次のようになります。

1. HTML/CSSの改善
2. JavaScriptによる入力支援
3. 入力値・存在する会社や弁当IDなどのバリデーション強化
4. テストの追加・拡充
5. Repository層などへの責務分離
6. Docker化
7. デプロイ環境への対応

特に `allergens` / `bento_allergens` は、注文画面の食品アレルギー表で利用しており、RDBの多対多関係を具体的に確認できます。

---

## 15. 最終的な目的

このデモの目的は、高機能なWebアプリケーションを作ることではありません。

**「業務上のデータをRDBでどのように表現し、それをFastAPIからどのように扱うか」**

を、小さく分かりやすい実例として説明できるようにすることを目的としています。

特に、

```mermaid
flowchart LR
    A[業務上の概念]
    B[RDBのテーブル]
    C[SQL]
    D[Pydanticモデル]
    E[FastAPI]
    F[HTML]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
```

という流れを一つのアプリケーションで確認できることを重視しています。
