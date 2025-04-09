import time
from celery.result import AsyncResult
from celery.app.control import Control
from celery.contrib.abortable import AbortableAsyncResult
from celery_app import app, convert_pdf_to_markdown
from typing import List, Dict
from datetime import datetime
import gradio as gr
import os

# 配置和 redis 接口
from config import QUEUE_SIZE, RESULT_DIR, r

STATE_COLOR_MAP = {
  "PENDING": "rgba(255, 193, 7, 0.7)",     # 琥珀色 70%, 等待/准备状态 - 柔和的琥珀色（中性等待状态）
  "STARTED": "rgba(33, 150, 243, 0.7)",    # 蓝色 70%, 开始/进行中状态 - 温和的蓝色（行动中）
  "PROGRESS": "rgba(0, 188, 212, 0.7)",    # 青蓝色 70%, 进度状态 - 渐变的青蓝色（动态过程）
  "SUCCESS": "rgba(56, 142, 60, 0.75)",    # 绿色 75%, 成功状态 - 自然的叶绿色（安全/完成）
  "FAILURE": "rgba(239, 108, 100, 0.75)",  # 珊瑚红 75%, 失败状态 - 柔和的珊瑚红（警告）
  "REVOKED": "rgba(149, 117, 205, 0.75)",  # 紫灰色 75%, 撤销状态 - 灰紫色（终止/人工干预）
  "RETRY": "rgba(255, 152, 0, 0.75)",      # 橙黄色 75%, 重试状态 - 温暖的橙黄色（再次尝试）
  "UNKNOWN": "rgba(158, 158, 158, 0.7)",   # 灰色 70%, 未知状态 - 中性浅灰色（未知/不确定）
}

STATE_SYMBOL_MAP = {
  "PENDING": "⏳",
  "STARTED": "⌛️",
  "PROGRESS": "🚀",
  "SUCCESS": "✅",
  "FAILURE": "❌",
  "REVOKED": "🚫",
  "RETRY": "🔄",
  "UNKNOWN": "❓",
}

class TaskRegistry:
  def __init__(self, maxlen: int = 10):
    """初始化任务注册表，设置最大队列大小"""
    self.task_queue = []
    self.maxlen = maxlen

  def register_task(self, file_path: str, target_lang: str = None) -> str | None:
    """注册新任务，如果队列已满则返回False"""
    if len(self.task_queue) == self.maxlen:
      return None
    
    # 通过 redis 传输文件
    with open(file_path, "rb") as f:
      file_data = f.read()
    filename = os.path.basename(file_path)
    r.set(f"file:{filename}", file_data)
    
    task = convert_pdf_to_markdown.delay(
      filename=filename,
      target_lang=target_lang
    )

    self.task_queue.append((task.id, filename))
    return task.id

  def get_all_task_ids(self) -> List[str]:
    """获取所有已知任务ID"""
    return map(lambda item: item[0], self.task_queue)

  def remove_task(self, i):
    """删除队列第 i 个任务，并刷新显示的队列组件"""
    if i < 0 or i >= self.maxlen:
      return
    
    task_id, pdf_file_name = self.task_queue[i]
    result = AbortableAsyncResult(task_id, app=app)
    state = result.state
    
    ctl: Control = app.control
    if state == "PENDING":
      ctl.revoke(task_id, terminate=True)  # 从 redis 队列中删除任务
    else:
      result.abort()  # 任务正在运行执行, 通知任务应该终止, Worker 将提前结束任务并清理

    # 删除 redis 中的文件和本地可能保存的执行结果文件
    _ = r.delete(f"file:{pdf_file_name}")
    if state == "SUCCESS":
      result_filename = result.result
      result_file_path = f"{RESULT_DIR}/{result_filename}"
      _ = r.delete(f"file:{result_filename}")
      if os.path.exists(result_file_path):
        os.remove(result_file_path)
    
    # 删除第 i 个元素
    del self.task_queue[i]

    return True

  def get_task_status(self, task_id: str) -> Dict:
    """获取单个任务状态"""
    result = AsyncResult(task_id, app=app)
    
    if not result.ready() and not result.state == 'PROGRESS':
      # 检查是否是活动任务（Celery inspector有时不可靠）
      inspector = app.control.inspect()
      active_tasks = inspector.active() or {}
      for worker, tasks in active_tasks.items():
        if any(t['id'] == task_id for t in tasks):
          result.state = 'PROGRESS'
    
    task_info = {
      'id': task_id,
      'state': result.state,
      'progress': 0,
      'timestamp': datetime.now().isoformat(),
      'result': result.result if result.ready() and result.successful() else None
    }
    
    # 从任务状态中提取进度信息
    if result.state == 'PROGRESS' and result.info and isinstance(result.info, dict):
      task_info['progress'] = result.info.get('progress', 0)
      task_info['timestamp'] = result.info.get('timestamp', task_info['timestamp'])
    elif result.ready():
      if result.successful():
        task_info['progress'] = 100
        if isinstance(result.result, dict):
          task_info.update(result.result)
      else:
        task_info['progress'] = 0
    
    return task_info
  
  def update_all_tasks(self):
    """更新所有 gradio 组件状态"""
    tasks = [self.get_task_status(task_id) for task_id in self.get_all_task_ids()]
    
    outputs = [gr.update(visible=False)] * (QUEUE_SIZE * 5)  # 默认全部隐藏
      
    for i, task in enumerate(tasks):
      if i >= QUEUE_SIZE:  # 不超过最大行数
        break
      state = task.get('state', 'UNKNOWN')
      # 更新第 i 行的组件
      outputs[i*5 + 0] = gr.update(
        value=[
          (STATE_SYMBOL_MAP[state], state),
          (task['id'], None),
        ],
        color_map=STATE_COLOR_MAP,
        visible=True
      )
      outputs[i*5 + 1] = gr.update(value=task.get('timestamp', 'N/A')[:-7], visible=True)
      outputs[i*5 + 2] = gr.update(value=f"{task.get('progress', 0)}%", visible=True)
      if state=='SUCCESS':
        result_filename = task['result']
        result_file_path = f"{RESULT_DIR}/{result_filename}"
        if not os.path.exists(result_file_path):
          file_data = r.get(f"file:{result_filename}")
          with open(result_file_path, 'wb') as f:
            f.write(file_data)
        outputs[i*5 + 3] = gr.update(value=result_file_path, visible=True, interactive=True)
      else:
        outputs[i*5 + 3] = gr.update(visible=True, interactive=False)
      outputs[i*5 + 4] = gr.update(visible=True, interactive=True)
    return outputs
