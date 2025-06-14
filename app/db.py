import asyncpg
from settings import DATABASE_URL

db_pool = None


async def init_db_pool():
    global db_pool
    db_pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=1,
        max_size=10,  # tune based on your PostgreSQL server
    )


def with_db_connection(func):
    async def wrapper(*args, **kwargs):
        async with db_pool.acquire() as conn:
            return await func(conn, *args, **kwargs)

    return wrapper


@with_db_connection
async def check_if_car_exists(conn, url: str) -> bool:
    """
    Check if a car with the given URL already exists in the database.
    """
    query = "SELECT EXISTS(SELECT 1 FROM cars WHERE url  = $1)"
    result = await conn.fetchval(query, url)
    return result is True


@with_db_connection
async def insert_car(
    conn,
    url: str,
    title: str,
    price_usd: int,
    odometer: int,
    username: str,
    phone_number: int,
    image_url: str,
    images_count: int,
    car_number: str,
    car_vin: str,
) -> None:
    """
    Insert a new car into the database.
    """
    query = """
        INSERT INTO cars (
            url, title, price_usd, odometer, username, phone_number,
            image_url, images_count, car_number, car_vin, datetime_found
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
    """
    await conn.execute(
        query,
        url,
        title,
        price_usd,
        odometer,
        username,
        phone_number,
        image_url,
        images_count,
        car_number,
        car_vin,
    )
