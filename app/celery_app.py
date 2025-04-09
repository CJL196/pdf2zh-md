from celery import Celery
from typing import Dict
from config import REDIS_URL

app = Celery(
  'pdf_tasks',
  broker=REDIS_URL,
  backend=REDIS_URL,
  task_serializer='json',
  accept_content=['json'],
  result_serializer='json'
)

@app.task(bind=True)
def convert_pdf_to_markdown(self, filename: str, target_lang: str = None) -> Dict:
  pass