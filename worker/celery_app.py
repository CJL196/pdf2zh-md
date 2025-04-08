from celery import Celery
import time
from datetime import datetime
from celery.contrib.abortable import AbortableTask

# 加载配置和 redis 接口
from config import config, r

app = Celery(
  'pdf_tasks',
  broker=f'redis://{config.redis.host}:6379/{config.redis.db}',
  backend=f'redis://{config.redis.host}:6379/{config.redis.db}',
  task_serializer='json',
  accept_content=['json'],
  result_serializer='json'
)

@app.task(base=AbortableTask, bind=True)
def convert_pdf_to_markdown(self, filename: str, target_lang: str = None) -> str:
  try:
    # 初始状态更新
    self.update_state(
      state='PROGRESS',
      meta={
        'progress': 0,
        'status': '开始处理',
        'timestamp': datetime.now().isoformat()
      }
    )
    
    # 模拟分阶段处理过程，每个阶段结束检查取消状态
    for i in range(1, 100):
      if self.is_aborted():  # 检查取消状态
        self.update_state(state='REVOKED')
        return 'Task cancelled'
      progress = i
      self.update_state(
        state='PROGRESS', 
        meta={
          'progress': progress,
          'status': f'处理中... {progress}%',
          'timestamp': datetime.now().isoformat()
        }
      )
      time.sleep(0.1)  # 模拟处理耗时
    
    # 处理完成，结果文件传入 redis
    result_file_name = f"{filename}_converted.md"
    r.set(f"file:{result_file_name}", "# Hello world!")

    return result_file_name
  
  except Exception as e:
    self.update_state(
      state='FAILURE',
      meta={
        'progress': 0,
        'error': str(e),
        'message': f'转换失败: {str(e)}',
        'timestamp': datetime.now().isoformat()
      }
    )
    raise  # 重新抛出异常以便Celery记录失败状态