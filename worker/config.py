from omegaconf import OmegaConf
from dotenv import load_dotenv
import os

import redis

# 加载配置
config = OmegaConf.load('config.yaml')

# 加载 .env 环境变量
load_dotenv()

# 确保临时目录存在
os.makedirs(config.paths.temp_dir, exist_ok=True)

config.api.key = os.getenv("API_KEY")

# 连接 redis
r = redis.Redis(
  host=config.redis.host,
  port=config.redis.port,
  db=config.redis.db
)