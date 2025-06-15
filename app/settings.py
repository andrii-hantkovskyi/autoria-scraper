import logging
import os

from environs import Env

env = Env()
env.read_env()

logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PER_PAGE = 50
BASE_URL = "https://auto.ria.com/uk/search/?lang_id=4&indexName=auto&custom=1&abroad=2"
PHONE_NUMBER_API_URL = "https://auto.ria.com/users/phones/{car_id}?hash={hash}&expires={expires}"

DATABASE_URL = env.str("DATABASE_URL", "postgresql://user:password@localhost:5432/auto_ria")
DATABASE_DUMPS_PATH = os.path.join(BASE_DIR, "..", "dumps")
