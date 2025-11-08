import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# ============================
# 1. 設定
# ============================
print("=" * 50)
print("BigQueryアップロード開始")
print("=" * 50)

# GCP設定
PROJECT_ID = "wheel-chair-analysis"
DATASET_ID = "tourism_barrier_free"
TABLE_ID = "attractions"
CREDENTIALS_PATH = "wheel-chair-analysis-63503d5a1864.json"

# データファイルパス
DATA_PATH = "data/processed/osm_tourism_cleaned.csv"

# ============================
# 2. 認証情報の設定
# ============================
print("\n認証情報を読み込み中...")

if not os.path.exists(CREDENTIALS_PATH):
    print(f"❌ エラー: {CREDENTIALS_PATH} が見つかりません")
    exit(1)

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=["https://www.googleapis.com/auth/bigquery"]
)

client = bigquery.Client(
    credentials=credentials,
    project=PROJECT_ID
)

print(f"✅ プロジェクト: {PROJECT_ID}")

# ============================
# 3. データセット作成（存在しない場合）
# ============================
print(f"\nデータセット '{DATASET_ID}' を確認中...")

dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

try:
    client.get_dataset(dataset_ref)
    print(f"✅ データセット既存: {DATASET_ID}")
except Exception:
    # データセット作成
    try:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-northeast1"  # 東京リージョン
        dataset.description = "観光地のバリアフリー対応状況データ"
        client.create_dataset(dataset)
        print(f"✅ データセット作成完了: {DATASET_ID}")
    except Exception as e:
        # 既に存在する場合もOK
        if "Already Exists" in str(e):
            print(f"✅ データセット既存: {DATASET_ID}")
        else:
            raise

# ============================
# 4. データ読み込み
# ============================
print(f"\nデータ読み込み中: {DATA_PATH}")

if not os.path.exists(DATA_PATH):
    print(f"❌ エラー: {DATA_PATH} が見つかりません")
    exit(1)

df = pd.read_csv(DATA_PATH)
print(f"✅ {len(df)}件のデータを読み込み")

# ============================
# 5. スキーマ定義
# ============================
print("\nスキーマ定義中...")

schema = [
    bigquery.SchemaField("osm_id", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("osm_type", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("city", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("unified_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("name_ja", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("name_en", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("tourism", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("lat", "FLOAT", mode="NULLABLE"),
    bigquery.SchemaField("lon", "FLOAT", mode="NULLABLE"),
    bigquery.SchemaField("bf_score", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("bf_category", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("wheelchair", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("wheelchair_description", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("toilets_wheelchair", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("wikidata", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("wikipedia", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("website", "STRING", mode="NULLABLE"),
]

print(f"✅ {len(schema)}フィールド定義完了")

# ============================
# 6. カラム名の調整（BigQuery用）
# ============================
# BigQueryはコロン(:)を含むカラム名を受け付けないため変換
df_upload = df.copy()
df_upload.columns = df_upload.columns.str.replace(':', '_')

print("\n✅ カラム名を調整:")
print(f"   例: 'name:ja' → 'name_ja'")

# ============================
# 7. テーブル作成設定
# ============================
table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

job_config = bigquery.LoadJobConfig(
    schema=schema,
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # 既存データを上書き
    source_format=bigquery.SourceFormat.CSV,
    skip_leading_rows=1,
    autodetect=False,
)

# ============================
# 8. BigQueryへアップロード
# ============================
print(f"\nBigQueryへアップロード中...")
print(f"  テーブル: {table_ref}")

try:
    # DataFrameから直接アップロード
    job = client.load_table_from_dataframe(
        df_upload,
        table_ref,
        job_config=job_config
    )

    # アップロード完了まで待機
    job.result()

    print(f"✅ アップロード完了！")

    # ============================
    # 9. アップロード結果確認
    # ============================
    print("\n" + "=" * 50)
    print("アップロード結果")
    print("=" * 50)

    table = client.get_table(table_ref)
    print(f"\n📊 テーブル情報:")
    print(f"  テーブルID: {table.table_id}")
    print(f"  行数: {table.num_rows:,}件")
    print(f"  サイズ: {table.num_bytes / 1024 / 1024:.2f} MB")
    print(f"  作成日時: {table.created}")

    # ============================
    # 10. サンプルクエリ実行
    # ============================
    print("\n" + "=" * 50)
    print("サンプルクエリ実行")
    print("=" * 50)

    # 都市別・カテゴリ別の件数を取得
    query = f"""
    SELECT
        city,
        bf_category,
        COUNT(*) as count
    FROM `{table_ref}`
    GROUP BY city, bf_category
    ORDER BY city, bf_category
    """

    print("\n実行クエリ:")
    print(query)
    print("\n結果:")

    query_job = client.query(query)
    results = query_job.result()

    for row in results:
        print(f"  {row.city:10s} | {row.bf_category:10s} | {row.count:4d}件")

    print("\n" + "=" * 50)
    print("✅ BigQueryアップロード完了！")
    print("=" * 50)

    print(f"\n📌 BigQueryコンソールで確認:")
    print(f"   https://console.cloud.google.com/bigquery?project={PROJECT_ID}&d={DATASET_ID}&t={TABLE_ID}&page=table")

except Exception as e:
    print(f"\n❌ エラーが発生しました:")
    print(f"   {str(e)}")
    exit(1)
