from omegaconf import OmegaConf
from openai import OpenAI
from dotenv import load_dotenv
import os
import redis

# 加载配置
config = OmegaConf.load('config.yaml')

REDIS_URL=f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
CLEAN_UP_TEMP=config.settings.cleanup_temp
MINERU_PATH=config.settings.mineru_path
TEMP_DIR=config.settings.temp_dir
MODEL=config.api.model

# 拼接 prompts
PROMPTS = ""
for p in config.prompts:
  PROMPTS += p

# 确保临时目录存在
os.makedirs(TEMP_DIR, exist_ok=True)

# 连接 redis
r = redis.Redis(
  host=config.redis.host,
  port=config.redis.port,
  db=config.redis.db
)

# 加载 .env 环境变量
load_dotenv()

# 连接 LLM
client = OpenAI(
  api_key=os.getenv("API_KEY"),
  base_url=config.api.base_url
)