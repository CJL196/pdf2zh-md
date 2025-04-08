from celery import Celery
from typing import Dict
from config import config

app = Celery(
  'pdf_tasks',
  broker=f'redis://{config.redis.host}:6379/{config.redis.db}',
  backend=f'redis://{config.redis.host}:6379/{config.redis.db}',
  task_serializer='json',
  accept_content=['json'],
  result_serializer='json'
)

@app.task(bind=True)
def convert_pdf_to_markdown(self, filename: str, target_lang: str = None) -> Dict:
  pass