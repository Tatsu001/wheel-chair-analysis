-- ====================================================================
-- 観光地バリアフリー分析 SQLクエリ集
-- ====================================================================
-- プロジェクト: wheel-chair-analysis
-- データセット: tourism_barrier_free
-- テーブル: attractions
-- 作成日: 2025-11-08
-- ====================================================================

-- ====================================================================
-- 1. 基本集計：都市別・カテゴリ別の件数
-- ====================================================================
-- 用途: ダッシュボードのメインKPI表示
-- 出力: city, bf_category, count, percentage
-- ====================================================================

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
    END;


-- ====================================================================
-- 2. 観光地タイプ別のバリアフリー対応状況
-- ====================================================================
-- 用途: どの観光施設タイプがBF対応が進んでいるか分析
-- 出力: tourism, total_count, bf_info_count, bf_info_rate
-- ====================================================================

SELECT
    tourism,
    COUNT(*) as total_count,
    SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) as bf_info_count,
    ROUND(SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as bf_info_rate,
    SUM(CASE WHEN bf_category = '対応済' THEN 1 ELSE 0 END) as accessible_count,
    SUM(CASE WHEN bf_category = '部分対応' THEN 1 ELSE 0 END) as partial_count
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY tourism
HAVING COUNT(*) >= 10  -- 10件以上あるタイプのみ
ORDER BY bf_info_rate DESC;


-- ====================================================================
-- 3. 都市別の観光地タイプ分布
-- ====================================================================
-- 用途: 各都市にどんな観光施設が多いか把握
-- 出力: city, tourism, count
-- ====================================================================

SELECT
    city,
    tourism,
    COUNT(*) as count
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY city, tourism
ORDER BY city, count DESC;


-- ====================================================================
-- 4. バリアフリースコア分布
-- ====================================================================
-- 用途: スコアの分布を可視化（ヒストグラム用）
-- 出力: score_range, count
-- ====================================================================

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
    END;


-- ====================================================================
-- 5. バリアフリー設備別の設置率
-- ====================================================================
-- 用途: どの設備が多く設置されているか分析
-- 出力: facility, installed_count, rate
-- ====================================================================

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

ORDER BY rate DESC;


-- ====================================================================
-- 6. バリアフリー対応施設ランキング（スコア上位20）
-- ====================================================================
-- 用途: ダッシュボードでのベストプラクティス表示
-- 出力: ranking, city, name, tourism, bf_score, bf_category
-- ====================================================================

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
LIMIT 20;


-- ====================================================================
-- 7. 都市別のバリアフリー対応率比較
-- ====================================================================
-- 用途: 都市間の対応状況を比較
-- 出力: city, total, accessible_rate, partial_rate, unknown_rate
-- ====================================================================

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
ORDER BY accessible_rate DESC;


-- ====================================================================
-- 8. 地図可視化用：座標付きバリアフリー対応施設
-- ====================================================================
-- 用途: Tableau等での地図プロット用
-- 出力: 座標、名前、スコア等（不明を除外）
-- ====================================================================

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
ORDER BY city, bf_score DESC;


-- ====================================================================
-- 9. サマリー統計（KPI一覧）
-- ====================================================================
-- 用途: ダッシュボードのトップKPI表示
-- 出力: 全体の統計サマリー
-- ====================================================================

SELECT
    COUNT(*) as total_attractions,
    COUNT(DISTINCT city) as total_cities,
    COUNT(DISTINCT tourism) as total_tourism_types,
    SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) as bf_info_available,
    ROUND(SUM(CASE WHEN bf_category != '不明' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as bf_info_rate,
    SUM(CASE WHEN bf_category = '対応済' THEN 1 ELSE 0 END) as fully_accessible,
    ROUND(AVG(bf_score), 2) as avg_bf_score,
    MAX(bf_score) as max_bf_score
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`;


-- ====================================================================
-- 10. 観光地タイプ×都市のクロス集計
-- ====================================================================
-- 用途: ピボットテーブル／ヒートマップ作成用
-- 出力: tourism, tokyo_count, osaka_count, nagoya_count
-- ====================================================================

SELECT
    tourism,
    SUM(CASE WHEN city = 'Tokyo' THEN 1 ELSE 0 END) as tokyo_count,
    SUM(CASE WHEN city = 'Osaka' THEN 1 ELSE 0 END) as osaka_count,
    SUM(CASE WHEN city = 'Nagoya' THEN 1 ELSE 0 END) as nagoya_count,
    COUNT(*) as total
FROM `wheel-chair-analysis.tourism_barrier_free.attractions`
GROUP BY tourism
ORDER BY total DESC;
