#!/usr/bin/env bash

set -euo pipefail

DB_NAME="${DB_NAME:-demo_db}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(uname -s)" != "Darwin" ]]; then
    printf 'このセットアップスクリプトはmacOS専用です。\n' >&2
    exit 1
fi

for command_name in psql createdb; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf 'PostgreSQLコマンド %s が見つかりません。\n' "$command_name" >&2
        printf 'Homebrewでインストールして起動してください:\n' >&2
        printf '  brew install postgresql\n  brew services start postgresql\n' >&2
        exit 1
    fi
done

if [[ ! "$DB_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    printf 'DB_NAMEは英字またはアンダースコアで始まる英数字にしてください。\n' >&2
    exit 1
fi

if ! psql -d postgres -Atqc 'SELECT 1' >/dev/null 2>&1; then
    printf 'PostgreSQLサーバーに接続できません。次を実行してください:\n' >&2
    printf '  brew services start postgresql\n' >&2
    exit 1
fi

database_exists="$(psql -d postgres -Atqc \
    "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")"
if [[ "$database_exists" != "1" ]]; then
    createdb "$DB_NAME"
    printf 'データベース %s を作成しました。\n' "$DB_NAME"
else
    printf 'データベース %s は既にあります。\n' "$DB_NAME"
fi

psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -c '
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )'

existing_table_count="$(psql -d "$DB_NAME" -Atqc "
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'public'
        AND table_name IN (
            'companies', 'bento', 'allergens', 'orders',
            'order_items', 'bento_allergens'
        )")"

if [[ "$existing_table_count" != "0" && "$existing_table_count" != "6" ]]; then
    printf '既存スキーマが不完全です。DBを変更せず停止しました。\n' >&2
    exit 1
fi

if [[ "$existing_table_count" == "6" ]]; then
    existing_column_count="$(psql -d "$DB_NAME" -Atqc "
        SELECT COUNT(*)
        FROM information_schema.columns AS actual
        JOIN (VALUES
            ('companies', 'id'), ('companies', 'name'),
            ('companies', 'contact_name'), ('companies', 'email'),
            ('companies', 'phone'),
            ('bento', 'id'), ('bento', 'name'), ('bento', 'price'),
            ('allergens', 'id'), ('allergens', 'name'),
            ('orders', 'id'), ('orders', 'company_id'),
            ('orders', 'order_date'), ('orders', 'created_at'),
            ('order_items', 'order_id'), ('order_items', 'bento_id'),
            ('order_items', 'quantity'),
            ('bento_allergens', 'bento_id'),
            ('bento_allergens', 'allergen_id')
        ) AS expected(table_name, column_name)
            ON expected.table_name = actual.table_name
            AND expected.column_name = actual.column_name
        WHERE actual.table_schema = 'public'")"

    if [[ "$existing_column_count" != "19" ]]; then
        printf '既存テーブルの列が想定と異なります。DBを変更せず停止しました。\n' >&2
        exit 1
    fi

    schema_version="$(psql -d "$DB_NAME" -Atqc \
        "SELECT 1 FROM schema_migrations WHERE version = '001_create_schema.sql'")"
    if [[ "$schema_version" != "1" ]]; then
        psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -c \
            "INSERT INTO schema_migrations (version) VALUES ('001_create_schema.sql')"
        printf '既存スキーマを確認し、初期スキーマとして記録しました。\n'
    fi
fi

for migration in "$PROJECT_ROOT"/migrations/*.sql; do
    version="$(basename "$migration")"
    applied="$(psql -d "$DB_NAME" -Atqc \
        "SELECT 1 FROM schema_migrations WHERE version = '$version'")"

    if [[ "$applied" == "1" ]]; then
        printf '適用済み: %s\n' "$version"
        continue
    fi

    printf '適用中: %s\n' "$version"
    psql -d "$DB_NAME" --single-transaction -v ON_ERROR_STOP=1 \
        -f "$migration"
done

printf '\nDBの準備ができました。アプリを起動するには:\n'
printf '  cd %q\n  uv sync\n  uv run uvicorn app.main:app --reload\n' "$PROJECT_ROOT"