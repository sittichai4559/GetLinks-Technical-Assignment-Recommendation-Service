CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    age INT NOT NULL,
    country VARCHAR(2) NOT NULL,
    subscription_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE content (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255),
    genre VARCHAR(50),
    popularity_score DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_watch_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    content_id BIGINT REFERENCES content(id),
    watched_at TIMESTAMP DEFAULT NOW()
);