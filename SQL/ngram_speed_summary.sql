WITH vars AS (
    SELECT
        'a287befc-0570-4eb3-a5d7-46653054cf0f'::text AS user_id,
        'deb70588-7fcf-4437-b122-f1f2a5113cdf'::text AS keyboard_id,
        '4c4d3e43-c5ba-4f62-8c1d-77dff0ee8e6b'::text AS session_id
),
session_ngrams AS (
    SELECT DISTINCT
        sns.ngram_text,
        sns.ngram_size,
        sns.session_dt
    FROM session_ngram_summary AS sns
    INNER JOIN vars
        ON vars.session_id = sns.session_id
),
total_instance_cnt AS (
    SELECT
        sns.ngram_text,
        sns.ngram_size,
        SUM(sns.instance_count) AS instances
    FROM 
        session_ngram_summary AS sns
        cross join vars 
    WHERE
        sns.session_dt <= (select start_time from practice_sessions where session_id = vars.session_id)
    GROUP BY
        sns.ngram_text,
        sns.ngram_size
),
keyboard_speed AS (
    SELECT
        COALESCE(k.target_ms_per_keystroke, 600) AS target_speed_ms
    FROM keyboards AS k
    INNER JOIN vars
        ON vars.keyboard_id = k.keyboard_id
    LIMIT 1
),
in_scope_rows AS (
    SELECT
        sns.ngram_text,
        sns.ngram_size,
        ngr.session_dt,
        sns.avg_ms_per_keystroke,
        sns.instance_count,
        ROW_NUMBER() OVER (
            PARTITION BY sns.ngram_text, sns.ngram_size
            ORDER BY sns.session_dt DESC
        ) AS row_num
    FROM session_ngram_summary AS sns
        INNER JOIN session_ngrams AS ngr
            ON ngr.ngram_text = sns.ngram_text
        AND ngr.ngram_size = sns.ngram_size
            cross join vars 
    WHERE
        sns.session_dt <= 
        (select start_time 
        from practice_sessions 
        where session_id = vars.session_id)
),
avg_calc AS (
    SELECT
        isr.ngram_text,
        isr.ngram_size,
        isr.session_dt,
        AVG(isr.avg_ms_per_keystroke) AS simple_avg_ms,
        SUM(isr.avg_ms_per_keystroke * (1 / row_num)) / SUM(1 / row_num) AS decaying_average_ms
    FROM in_scope_rows AS isr
    WHERE isr.row_num <= 20
    GROUP BY
        isr.ngram_text,
        isr.ngram_size,
        isr.session_dt
)
SELECT
    v.user_id,
    v.keyboard_id,
    v.session_id,
    a.ngram_text,
    a.ngram_size,
    a.decaying_average_ms,
    k.target_speed_ms,
    CASE
        WHEN COALESCE(a.decaying_average_ms, 0) > 0
            THEN 100.0 * COALESCE(k.target_speed_ms, 600) / a.decaying_average_ms
        ELSE 0
    END AS target_performance_pct,
    CASE
        WHEN COALESCE(a.decaying_average_ms, 0) <= COALESCE(k.target_speed_ms, 600)
            THEN 1
        ELSE 0
    END AS meets_target,
COALESCE(tic.instances, 0) AS sample_count,
    CURRENT_TIMESTAMP AS updated_dt,
    a.session_dt
FROM avg_calc AS a
inner join Total_instance_cnt tic
    on a.ngram_text = tic.ngram_text
    and a.ngram_size = tic.ngram_size
CROSS JOIN vars AS v
CROSS JOIN keyboard_speed AS k
order by a.ngram_size desc;