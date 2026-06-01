# 路线图

**English** | 简体中文

本路线图追踪 **DeepResearch on LangGraph** 的公开演进。
它与内部 `.comate/specs/` 中的计划保持一致,但有意精简,方便访问者一眼看到方向。

## Now — v0.2.x (Quality Foundation)
- [x] 质量基础脚手架:pytest 脚手架、配置漂移修复、`advanced` 搜索后端、SSE 协议测试。
- [x] CI 工作流(lint + tests)。
- [x] 公开文档:README、LICENSE、CHANGELOG、ROADMAP、CONTRIBUTING、SECURITY。
- [x] Docker + docker-compose,可选用 Ollama profile。
- [ ] 在 README 中加入公开演示/截屏链接。

## Next — v0.3.x (Search Reliability)
- [ ] `_search_advanced` 中并发后端扇出(`asyncio.gather`,每个后端独立超时)。
- [ ] 前端展示每个后端的延迟与结果数。
- [ ] `wiki_query` / `wiki_search` MCP 工具封装(目前在 `tools/`,未接入)。

## Later — v0.4.x (Agent Capability)
- [ ] ReAct agent 节点,使 LLM 可以自主决定何时调用 `note_tool` / `search_tool`。
- [ ] 区域感知提示词(English / 中文 / 日本語),根据前端语言自动切换。
- [ ] HTTP Runtime API 加固:`POST /v1/research` 与 `/v1/sessions`。

## Stretch — v1.0
- [ ] 稳定的公开 API,以便在 IDE 与 Web UI 中嵌入 agent。
- [ ] 一流的评测框架,基于留出的研究基准。
- [ ] 分布式研究 worker(多租户调度)。

每个里程碑的详细设计请参见 `.comate/specs/`。
