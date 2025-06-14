CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    url VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    price_usd INTEGER NOT NULL,
    odometer INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,
    phone_number BIGINT NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    images_count INTEGER NOT NULL,
    car_number VARCHAR(255) NOT NULL,
    car_vin VARCHAR(255) NOT NULL,
    datetime_found TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
