import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# ============================
# 1. 設定
# ============================
print("=" * 60)
print("SQL集計クエリ実行 & CSV出力")
print("=" * 60)

# GCP設定
PROJECT_ID = "wheel-chair-analysis"
CREDENTIALS_PATH = "wheel-chair-analysis-63503d5a1864.json"
OUTPUT_DIR = "data/aggregated"

# 出力フォルダ作成
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================
# 2. 認証情報の設定
# ============================
print("\n認証情報を読み込み中...")

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
# 3. クエリを直接定義
# ============================
queries = [
    {
        'number': '01',
        'name': '都市別_カテゴリ別件数',
        'query': """
SELECT
    city,
    bf_category,
    COUNT(*) as attraction_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY city), 2) as percentage
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY city, bf_category
ORDER BY city,
    CASE bf_category
        WHEN '対応済' THEN 1
        WHEN '部分対応' THEN 2
        WHEN '未対応' THEN 3
        WHEN '不明' THEN 4
    END
"""
    },
    {
        'number': '02',
        'name': '観光地タイプ別BF対応状況',
        'query': """
SELECT
    tourism,
    COUNT(*) as total_count,
    SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) as bf_info_count,
    ROUND(SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as bf_info_rate,
    SUM(CASE WHEN bf_category = '対応済' THEN 1 ELSE 0 END) as accessible_count,
    SUM(CASE WHEN bf_category = '部分対応' THEN 1 ELSE 0 END) as partial_count
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY tourism
HAVING COUNT(*) >= 10
ORDER BY bf_info_rate DESC
"""
    },
    {
        'number': '03',
        'name': '都市別観光地タイプ分布',
        'query': """
SELECT
    city,
    tourism,
    COUNT(*) as count
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY city, tourism
ORDER BY city, count DESC
"""
    },
    {
        'number': '04',
        'name': 'BFスコア分布',
        'query': """
SELECT
    CASE
        WHEN bf_score = 0 THEN '0点（不明）'
        WHEN bf_score <= 20 THEN '1-20点（未対応）'
        WHEN bf_score <= 40 THEN '21-40点（部分対応）'
        WHEN bf_score <= 60 THEN '41-60点（対応済）'
        ELSE '61-100点（対応済）'
    END as score_range,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY score_range
ORDER BY
    CASE score_range
        WHEN '0点（不明）' THEN 0
        WHEN '1-20点（未対応）' THEN 1
        WHEN '21-40点（部分対応）' THEN 2
        WHEN '41-60点（対応済）' THEN 3
        ELSE 4
    END
"""
    },
    {
        'number': '05',
        'name': 'BF設備別設置率',
        'query': """
SELECT
    '車いす対応トイレ' as facility,
    SUM(CASE WHEN toilets_wheelchair = 'yes' THEN 1 ELSE 0 END) as installed_count,
    ROUND(SUM(CASE WHEN toilets_wheelchair = 'yes' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as rate
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`

UNION ALL

SELECT
    '車いす対応（全般）' as facility,
    SUM(CASE WHEN wheelchair IN ('yes', 'designated') THEN 1 ELSE 0 END) as installed_count,
    ROUND(SUM(CASE WHEN wheelchair IN ('yes', 'designated') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as rate
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`

ORDER BY rate DESC
"""
    },
    {
        'number': '06',
        'name': 'BF対応施設TOP20',
        'query': """
SELECT
    ROW_NUMBER() OVER (ORDER BY bf_score DESC, unified_name) as ranking,
    city,
    unified_name as name,
    tourism,
    bf_score,
    bf_category,
    wheelchair,
    toilets_wheelchair
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
WHERE bf_score > 0
ORDER BY bf_score DESC, unified_name
LIMIT 20
"""
    },
    {
        'number': '07',
        'name': '都市別BF対応率比較',
        'query': """
SELECT
    city,
    COUNT(*) as total_attractions,
    SUM(CASE WHEN bf_category = '対応済' THEN 1 ELSE 0 END) as accessible_count,
    ROUND(SUM(CASE WHEN bf_category = '対応済' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as accessible_rate,
    SUM(CASE WHEN bf_category = '部分対応' THEN 1 ELSE 0 END) as partial_count,
    ROUND(SUM(CASE WHEN bf_category = '部分対応' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as partial_rate,
    SUM(CASE WHEN bf_category = '不明' THEN 1 ELSE 0 END) as unknown_count,
    ROUND(SUM(CASE WHEN bf_category = '不明' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as unknown_rate
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY city
ORDER BY accessible_rate DESC
"""
    },
    {
        'number': '08',
        'name': '地図用_BF対応施設データ',
        'query': """
SELECT
    city,
    unified_name,
    tourism,
    lat,
    lon,
    bf_score,
    bf_category,
    wheelchair,
    toilets_wheelchair,
    website
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
WHERE bf_category != '不明'
    AND lat IS NOT NULL
    AND lon IS NOT NULL
ORDER BY city, bf_score DESC
"""
    },
    {
        'number': '09',
        'name': 'サマリー統計_KPI',
        'query': """
SELECT
    COUNT(*) as total_attractions,
    COUNT(DISTINCT city) as total_cities,
    COUNT(DISTINCT tourism) as total_tourism_types,
    SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) as bf_info_available,
    ROUND(SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as bf_info_rate,
    SUM(CASE WHEN bf_category = '対応済' THEN 1 ELSE 0 END) as fully_accessible,
    ROUND(AVG(bf_score), 2) as avg_bf_score,
    MAX(bf_score) as max_bf_score
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
"""
    },
    {
        'number': '10',
        'name': '観光地タイプ_都市クロス集計',
        'query': """
SELECT
    tourism,
    SUM(CASE WHEN city = 'Tokyo' THEN 1 ELSE 0 END) as tokyo_count,
    SUM(CASE WHEN city = 'Osaka' THEN 1 ELSE 0 END) as osaka_count,
    SUM(CASE WHEN city = 'Nagoya' THEN 1 ELSE 0 END) as nagoya_count,
    COUNT(*) as total
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY tourism
ORDER BY total DESC
"""
    }
]

print(f"✅ {len(queries)}個のクエリを定義")

# ============================
# 4. 各クエリを実行してCSV保存
# ============================
print("\n" + "=" * 60)
print("クエリ実行開始")
print("=" * 60)

results = []

for i, q in enumerate(queries, 1):
    number = q['number']
    name = q['name']
    query = q['query']

    print(f"\n[{i}/{len(queries)}] {number}. {name}")
    print("-" * 60)

    try:
        # クエリ実行
        print("実行中...")
        query_job = client.query(query)
        df = query_job.result().to_dataframe()

        # ファイル名生成
        filename = f"{number}_{name}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # CSV保存
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        print(f"✅ 完了: {len(df)}行")
        print(f"   保存先: {filepath}")

        # 最初の3行を表示
        if len(df) > 0:
            print(f"\n   プレビュー:")
            print(df.head(3).to_string(index=False))

        results.append({
            'number': number,
            'name': name,
            'rows': len(df),
            'columns': len(df.columns),
            'file': filename,
            'status': 'Success'
        })

    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        results.append({
            'number': number,
            'name': name,
            'rows': 0,
            'columns': 0,
            'file': '',
            'status': f'Error'
        })

# ============================
# 5. 実行結果サマリー
# ============================
print("\n" + "=" * 60)
print("実行結果サマリー")
print("=" * 60)

results_df = pd.DataFrame(results)
print(f"\n{results_df.to_string(index=False)}")

# 成功・失敗の集計
success_count = len([r for r in results if r['status'] == 'Success'])
error_count = len(results) - success_count

print(f"\n✅ 成功: {success_count}件")
if error_count > 0:
    print(f"❌ 失敗: {error_count}件")

print(f"\n📁 出力フォルダ: {OUTPUT_DIR}")
print(f"   合計ファイル数: {success_count}個")

# サマリーCSV保存
summary_path = os.path.join(OUTPUT_DIR, "_execution_summary.csv")
results_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
print(f"\n📊 実行サマリー保存: {summary_path}")

print("\n" + "=" * 60)
print("✅ SQL集計クエリ実行完了！")
print("=" * 60)
