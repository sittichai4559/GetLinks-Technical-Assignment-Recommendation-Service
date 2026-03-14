INSERT INTO users(age,country,subscription_type)
SELECT
    (18 + floor(random()*40))::int,
    (ARRAY['US','GB','CA','AU','DE'])[floor(random()*5)+1],
    (ARRAY['free','basic','premium'])[floor(random()*3)+1]
FROM generate_series(1,20);

INSERT INTO content(title,genre,popularity_score,created_at)
SELECT
    'Movie '||g,
    (ARRAY['action','drama','comedy','thriller','documentary'])[floor(random()*5)+1],
    random(),
    NOW() - (random()*1000 || ' days')::interval
FROM generate_series(1,50) g;

INSERT INTO user_watch_history(user_id,content_id,watched_at)
SELECT
    floor(random()*20)+1,
    floor(random()*50)+1,
    NOW() - (random()*365 || ' days')::interval
FROM generate_series(1,200);