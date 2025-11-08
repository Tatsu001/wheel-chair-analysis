import pandas as pd
import numpy as np
import os

# ============================
# 1. データ読み込み
# ============================
print("=" * 50)
print("データクリーニング開始")
print("=" * 50)

# 3都市のデータを読み込み
cities = ['tokyo', 'osaka', 'nagoya']
dfs = []

for city in cities:
    file_path = f'data/raw/osm_{city}_raw.csv'
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        print(f"\n✅ {city.capitalize()}: {len(df)}件読み込み")
        dfs.append(df)
    else:
        print(f"\n⚠️  {city.capitalize()}: ファイルなし")

# 結合
df_all = pd.concat(dfs, ignore_index=True)
print(f"\n📊 合計: {len(df_all)}件")
print(f"📊 列数: {len(df_all.columns)}列")

# ============================
# 2. 必要な列のみ抽出
# ============================
print("\n" + "=" * 50)
print("必要な列のみ抽出")
print("=" * 50)

# 必要な列を定義
required_cols = [
    # 基本情報
    'osm_id', 'osm_type', 'city', 'lat', 'lon',
    # 名前
    'name', 'name:ja', 'name:en',
    # 観光地タイプ
    'tourism',
    # バリアフリー関連
    'wheelchair', 'wheelchair:description',
    'toilets:wheelchair', 'elevator', 'ramp',
    'automatic_door', 'entrance', 'door:width', 'tactile_paving',
    # その他
    'description', 'wikidata', 'wikipedia', 'website'
]

# 存在する列のみ抽出
existing_cols = [col for col in required_cols if col in df_all.columns]
df = df_all[existing_cols].copy()

print(f"✅ {len(existing_cols)}列に絞り込み")
print(f"   抽出列: {existing_cols[:10]}... (他{len(existing_cols)-10}列)")

# ============================
# 3. 名前の統一（日本語優先）
# ============================
print("\n" + "=" * 50)
print("名前の統一（日本語優先）")
print("=" * 50)

def get_unified_name(row):
    """日本語名を優先して統一名を返す"""
    if pd.notna(row.get('name:ja')):
        return row['name:ja']
    elif pd.notna(row.get('name')):
        return row['name']
    elif pd.notna(row.get('name:en')):
        return row['name:en']
    else:
        return None

df['unified_name'] = df.apply(get_unified_name, axis=1)

# 名前がない施設を除外
before_count = len(df)
df = df[df['unified_name'].notna()].copy()
after_count = len(df)
print(f"✅ 名前あり: {after_count}件")
print(f"   除外: {before_count - after_count}件（名前なし）")

# ============================
# 4. バリアフリースコア計算
# ============================
print("\n" + "=" * 50)
print("バリアフリースコア計算")
print("=" * 50)

def calculate_bf_score(row):
    """バリアフリースコアを計算（0-100点）"""
    score = 0

    # wheelchair基本情報 (最大50点)
    wheelchair = row.get('wheelchair')
    if wheelchair == 'yes':
        score += 40
    elif wheelchair == 'designated':
        score += 50
    elif wheelchair == 'limited':
        score += 20
    elif wheelchair == 'no':
        score += 0
    # wheelchair情報なし → 0点

    # 詳細設備（各10-15点）
    if row.get('toilets:wheelchair') == 'yes':
        score += 15
    if row.get('elevator') == 'yes':
        score += 15
    if row.get('ramp') == 'yes':
        score += 10
    if row.get('automatic_door') == 'yes':
        score += 10
    if row.get('tactile_paving') == 'yes':
        score += 10

    return min(score, 100)  # 最大100点

df['bf_score'] = df.apply(calculate_bf_score, axis=1)

print(f"✅ スコア計算完了")
print(f"\nスコア分布:")
print(df['bf_score'].describe())

# ============================
# 5. カテゴリ分類
# ============================
print("\n" + "=" * 50)
print("カテゴリ分類")
print("=" * 50)

def classify_bf_category(score):
    """スコアからカテゴリ分類"""
    if score == 0:
        return '不明'
    elif score <= 20:
        return '未対応'
    elif score <= 50:
        return '部分対応'
    else:
        return '対応済'

df['bf_category'] = df['bf_score'].apply(classify_bf_category)

print(f"✅ カテゴリ分類完了")
print(f"\nカテゴリ別件数:")
print(df['bf_category'].value_counts())

# ============================
# 6. 重複削除
# ============================
print("\n" + "=" * 50)
print("重複削除")
print("=" * 50)

# 同じ名前・座標の施設は重複とみなす
before_count = len(df)
df = df.drop_duplicates(subset=['unified_name', 'lat', 'lon'], keep='first')
after_count = len(df)

print(f"✅ 重複削除完了")
print(f"   削除前: {before_count}件")
print(f"   削除後: {after_count}件")
print(f"   削除数: {before_count - after_count}件")

# ============================
# 7. 列の並び替え
# ============================
# 見やすい順に並び替え
column_order = [
    'osm_id', 'osm_type', 'city',
    'unified_name', 'name', 'name:ja', 'name:en',
    'tourism',
    'lat', 'lon',
    'bf_score', 'bf_category',
    'wheelchair', 'wheelchair:description',
    'toilets:wheelchair', 'elevator', 'ramp',
    'automatic_door', 'entrance', 'door:width', 'tactile_paving',
    'description', 'wikidata', 'wikipedia', 'website'
]

# 存在する列のみ並び替え
existing_order = [col for col in column_order if col in df.columns]
df = df[existing_order]

# ============================
# 8. 保存
# ============================
print("\n" + "=" * 50)
print("クリーニング済みデータ保存")
print("=" * 50)

os.makedirs('data/processed', exist_ok=True)
output_path = 'data/processed/osm_tourism_cleaned.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')

print(f"\n✅ 保存完了: {output_path}")
print(f"   行数: {len(df)}件")
print(f"   列数: {len(df.columns)}列")

# ============================
# 9. サマリー表示
# ============================
print("\n" + "=" * 50)
print("クリーニング結果サマリー")
print("=" * 50)

print(f"\n【都市別件数】")
print(df['city'].value_counts())

print(f"\n【観光地タイプ別件数】")
print(df['tourism'].value_counts())

print(f"\n【バリアフリーカテゴリ別件数】")
print(df['bf_category'].value_counts())

print(f"\n【スコア上位5施設】")
print(df.nlargest(5, 'bf_score')[['unified_name', 'city', 'tourism', 'bf_score', 'bf_category']])

print("\n" + "=" * 50)
print("✅ データクリーニング完了！")
print("=" * 50)
