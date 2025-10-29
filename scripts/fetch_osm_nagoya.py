import overpy
import pandas as pd
import os

# フォルダ作成
os.makedirs('data/raw', exist_ok=True)

# Overpass API初期化
api = overpy.Overpass()

# 名古屋市の観光施設を取得
query = """
[out:json][timeout:180];
(
  node["tourism"~"museum|attraction|gallery|theme_park|viewpoint|zoo|aquarium"](35.0,136.8,35.3,137.0);
  way["tourism"~"museum|attraction|gallery|theme_park|viewpoint|zoo|aquarium"](35.0,136.8,35.3,137.0);
  relation["tourism"~"museum|attraction|gallery|theme_park|viewpoint|zoo|aquarium"](35.0,136.8,35.3,137.0);
);
out body;
>;
out skel qt;
"""

print("名古屋市のOSMデータ取得中...")
result = api.query(query)

# tourismタグを持つ要素のみ抽出
tourism_data = []

for element in result.nodes + result.ways + result.relations:
    if 'tourism' not in element.tags:
        continue
    
    # 座標取得
    if hasattr(element, 'lat'):
        lat, lon = element.lat, element.lon
        osm_type = 'node'
    elif hasattr(element, 'center_lat'):
        lat, lon = element.center_lat, element.center_lon
        osm_type = 'way'
    else:
        lat, lon = None, None
        osm_type = 'way'
    
    row = {
        'osm_id': element.id,
        'osm_type': osm_type,
        'city': 'Nagoya',
        'lat': lat,
        'lon': lon,
        **element.tags
    }
    tourism_data.append(row)

# DataFrame作成・保存
df = pd.DataFrame(tourism_data)
output_path = 'data/raw/osm_nagoya_raw.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')

print(f"\n✅ 保存完了: {len(df)}件")
print(f"カラム数: {len(df.columns)}列")
print(f"保存先: {output_path}")

# データ概要表示
print("\n=== データ概要 ===")
print(f"wheelchair情報あり: {df['wheelchair'].notna().sum()}件")
print(f"名前あり: {df['name'].notna().sum()}件")
print(f"座標あり: {df['lat'].notna().sum()}件")

print("\n=== 最初の3件 ===")
print(df[['name', 'tourism', 'wheelchair', 'lat', 'lon']].head(3))