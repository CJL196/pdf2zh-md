from translate import Executor, ProgressTracker
from celery import Celery
from datetime import datetime
from celery.contrib.abortable import AbortableTask

# 加载配置
from config import REDIS_URL

app = Celery(
  'pdf_tasks',
  broker=REDIS_URL,
  backend=REDIS_URL,
  task_serializer='json',
  accept_content=['json'],
  result_serializer='json'
)

TRANSLATE_STEPS = [
# (任务, 该任务完成前的进度, 该任务完成后的进度)
  (Executor.step1, 0),
  (Executor.step2, 1),
  (Executor.step3, 2),
  (Executor.step4, 6),
  (Executor.step5, 7),
  (Executor.step6, 8, 98),
  (Executor.step7, 98),
  (Executor.step8, 99),
]

CONVERT_STEPS = [
# (任务, 该任务完成前的进度)
  (Executor.step1, 0),
  (Executor.step2, 1),
  (Executor.step3, 2),
  (Executor.step4, 96),
  (Executor.step5, 97),
  (Executor.step7, 98),
  (Executor.step8, 99),
]

@app.task(base=AbortableTask, bind=True)
def convert_pdf_to_markdown(self, filename: str, target_lang: str = None) -> str:
  executor = Executor(filename, target_lang)
  try:
    for step in CONVERT_STEPS if target_lang is None else TRANSLATE_STEPS:
      if executor.progress(self, step[1]):
        return "Aborted"
      if len(step)==3:
        tracker = ProgressTracker(self, executor, step[1], step[2])
        step[0](executor, tracker)
      else:
        step[0](executor)
    
    executor.clean_up()
    return f"{executor.pdf_name}.zip"
  
  except Exception as e:
    self.update_state(
      state='FAILURE',
      meta={
        'exc_type': type(e).__name__,
        'exc_message': e.__str__(),
        'progress': 0,
        'status': f'任务失败',
        'timestamp': datetime.now().isoformat()
      }
    )
    raise  # 重新抛出异常以便Celery记录失败状态