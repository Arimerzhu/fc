export const meta = {
  name: 'headless-backend-batch',
  description: 'Add batch execution mode to HeadlessBackend for multi-step workflows',
  phases: [
    { title: 'Implement', detail: 'Add batch_start/batch_add/batch_execute to HeadlessBackend' },
    { title: 'Test', detail: 'Write tests for batch mode and verify all pass' },
    { title: 'Review', detail: 'fc-review-agent reviews the implementation' },
  ],
}

// ── Phase 1: Implement batch mode in HeadlessBackend ──
phase('Implement')

const impl = await agent(
  '你是 fc-core-agent (opus, blue)，负责 HeadlessBackend 核心修复。\n\n' +
  '## 任务：为 HeadlessBackend 添加批量执行模式\n\n' +
  '**文件**: `D:\\桌面文件\\fc\\packages\\core\\src\\fc_core\\backend\\__init__.py`\n\n' +
  '**问题**: 当前每个公开方法（document_new, object_create, export 等）都独立调用 _execute_macro()，' +
  '每次 _execute_macro() 都 subprocess.run() 启动新 FreeCADCmd 进程。多步工作流中前一步的状态在下一步丢失。\n\n' +
  '**方案**: 添加批量执行模式 — 将多个操作累积到一个 Python 脚本中，用一次进程调用完成。\n\n' +
  '### 具体修改\n\n' +
  '在 HeadlessBackend 类中添加以下内容（放在 __init__ 和 connect 之间）：\n\n' +
  '```python\n    # ── Batch execution mode ──\n    def batch_start(self) -> None:\n        """Start batching operations into a single script.\n        \n        Call batch_start(), then use batch_add() to queue operations,\n        then batch_execute() to run them all in a single FreeCAD process.\n        """\n        self._batch_parts: list[str] = []\n        self._batch_doc_path: str | None = None\n\n    def batch_add(self, body: str) -> None:\n        """Add a Python code snippet to the batch script.\n        \n        Args:\n            body: Python code to execute in FreeCAD context.\n        """\n        if not hasattr(self, "_batch_parts"):\n            self.batch_start()\n        self._batch_parts.append(body)\n\n    def batch_execute(self, timeout: int | None = None) -> list[dict[str, Any]]:\n        """Execute all batched operations in a single FreeCAD process.\n        \n        Each operation is separated by a result marker so results can be\n        parsed individually. Returns a list of result dicts, one per\n        operation.\n        \n        Args:\n            timeout: Timeout in seconds (default: self._timeout).\n            \n        Returns:\n            List of result dicts with status/data/message keys.\n        """\n        if not hasattr(self, "_batch_parts") or not self._batch_parts:\n            return []\n        \n        # Build a combined script with per-operation markers\n        parts: list[str] = []\n        for i, body in enumerate(self._batch_parts):\n            parts.append(f"# --- operation_{i} ---")\n            parts.append(body)\n            parts.append(f"print(\'___FC_RESULT_{i}___\' + json.dumps(_fc_result, default=str))")\n        \n        combined_body = "\\n".join(parts)\n        script = self._build_wrapper_script(combined_body)\n        macro_path = self._write_macro(script)\n        try:\n            result = self._run([self.freecad_path, macro_path], timeout=timeout)\n            # Parse all results from stdout\n            results: list[dict[str, Any]] = []\n            for line in result.stdout.splitlines():\n                for i in range(len(self._batch_parts)):\n                    marker = f"___FC_RESULT_{i}___"\n                    if line.startswith(marker):\n                        results.append(json.loads(line[len(marker):]))\n            # Pad with error results if some markers were missing\n            while len(results) < len(self._batch_parts):\n                results.append({"status": "error", "data": {}, "message": "No result output"})\n            return results\n        finally:\n            try:\n                os.unlink(macro_path)\n            except OSError:\n                pass\n            self._batch_parts = []\n```\n\n' +
  '### 重要约束\n' +
  '1. 不要修改任何现有公开方法的实现（document_new, object_create 等保持原样）\n' +
  '2. batch_start/batch_add/batch_execute 是新增方法，不影响现有接口\n' +
  '3. batch_execute 返回 list[dict]，每个 dict 对应一个 batch_add 的结果\n' +
  '4. 在 _build_wrapper_script 中，_fc_result 变量在每个 batch_add 的代码片段中会被覆盖，' +
  '所以每个片段末尾需要 print 自己的结果标记\n' +
  '5. 确保 batch_execute 的 script 构建正确：所有操作共享同一个 FreeCAD 进程上下文\n' +
  '6. 添加 `from __future__ import annotations` 如果还没有（检查文件顶部）\n\n' +
  '请先 Read 文件确认上下文，再执行 Edit。',
  { label: 'implement', phase: 'Implement' }
)

if (!impl) {
  log('Implement agent returned null, skipping')
  return { success: false, error: 'Implement agent failed' }
}

log(`Implement complete: ${impl.substring(0, 200)}...`)

// ── Phase 2: Write tests ──
phase('Test')

const tests = await agent(
  '你是 fc-test-agent (opus, yellow)，负责测试。\n\n' +
  '## 任务：为 HeadlessBackend 批量执行模式编写测试\n\n' +
  '**测试文件**: `D:\\桌面文件\\fc\\packages\\core\\tests\\test_batch.py`（新建）\n\n' +
  '**被测代码**: `D:\\桌面文件\\fc\\packages\\core\\src\\fc_core\\backend\\__init__.py` 中的\n' +
  'HeadlessBackend.batch_start() / batch_add() / batch_execute() 方法\n\n' +
  '**测试要求**:\n' +
  '1. 测试 batch_start 初始化空批次\n' +
  '2. 测试 batch_add 累积操作（不立即执行）\n' +
  '3. 测试 batch_execute 合并多个操作到单次进程调用\n' +
  '4. 测试 batch_execute 返回每个操作的结果列表\n' +
  '5. 测试 batch_execute 空批次返回空列表\n' +
  '6. 测试 batch_execute 超时处理\n' +
  '7. 测试多步工作流：document_new → object_create → document_save 在单次 batch_execute 中完成\n' +
  '8. 测试向后兼容：原有单操作接口（document_new 等）仍然正常工作\n\n' +
  '**Mock 策略**:\n' +
  '- mock _run() 返回预设的 stdout（包含 ___FC_RESULT_0___ / ___FC_RESULT_1___ 标记）\n' +
  '- mock _write_macro() 返回临时路径\n' +
  '- 不要真正启动 FreeCAD\n\n' +
  '**已有测试参考**: 读取 `D:\\桌面文件\\fc\\packages\\core\\tests\\test_backend.py` 了解现有测试风格\n\n' +
  '请先 Read test_backend.py 了解风格，再创建 test_batch.py。\n' +
  '创建后运行 `pytest packages/core/tests/test_batch.py -x -q` 验证。',
  { label: 'test', phase: 'Test' }
)

if (!tests) {
  log('Test agent returned null, skipping')
  return { success: false, error: 'Test agent failed' }
}

log(`Tests complete: ${tests.substring(0, 200)}...`)

// ── Phase 3: Review ──
phase('Review')

const review = await agent(
  '你是 fc-review-agent (opus, red)，负责代码审查。\n\n' +
  '## 任务：审查 HeadlessBackend 批量执行模式实现\n\n' +
  '**实现文件**: `D:\\桌面文件\\fc\\packages\\core\\src\\fc_core\\backend\\__init__.py`\n' +
  '**测试文件**: `D:\\桌面文件\\fc\\packages\\core\\tests\\test_batch.py`\n\n' +
  '**审查要点**:\n' +
  '1. batch_start/batch_add/batch_execute 实现是否正确\n' +
  '2. 脚本合并逻辑是否安全（操作间状态共享）\n' +
  '3. 结果解析是否健壮（标记匹配、缺失处理）\n' +
  '4. 向后兼容性：原有公开方法是否未受影响\n' +
  '5. 测试覆盖是否充分\n' +
  '6. 是否有并发安全问题\n\n' +
  '**验证**:\n' +
  '- 运行 `pytest packages/core/tests/ -x -q` 确认所有测试通过\n' +
  '- 输出简洁审查报告（✅/❌ 每项 + 总结）',
  { label: 'review', phase: 'Review' }
)

log(`Review: ${review?.substring(0, 300) || 'null'}`)

return { success: true }
