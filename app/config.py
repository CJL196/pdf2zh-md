import os
from omegaconf import OmegaConf
import redis

# 加载配置
config = OmegaConf.load('config.yaml')

REDIS_URL=f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
QUEUE_SIZE = int(config.settings.queue_size)
RESULT_DIR = config.settings.result_dir

# 确保临时目录存在
os.makedirs(RESULT_DIR, exist_ok=True)

# 连接 redis
r = redis.Redis(
  host=config.redis.host,
  port=config.redis.port,
  db=config.redis.db
)

r.ping()