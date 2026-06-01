# 贡献指南

**English** | 简体中文

感谢你有兴趣为本项目做出贡献!这是一个基于 LangGraph 的深度研究 Agent,搭配 Vue 3 前端。
Issue、PR 和 Discussions 全部欢迎。

## 开发环境准备

前置依赖:
- Python `>=3.10,<3.15`
- [uv](https://docs.astral.sh/uv/) 用于 Python 依赖管理
- Node.js `>=20` 用于前端

```bash
# 后端
cd backend
uv sync
cp .env.example .env  # 然后填入 API 密钥

# 前端
cd ../frontend
npm install
```

## 运行测试

```bash
cd backend
uv run ruff check src tests
uv run pytest
```

针对 SSE 流的集成测试快速且离线;测试通过 monkeypatch 替换 agent,无需真实 API 密钥即可验证协议。

## 提交 Pull Request

1. Fork 仓库并创建特性分支(`feat/<name>`、`fix/<name>`、`docs/<name>`)。
2. 保持 PR 小而专注,一个 PR 只解决一个问题。
3. 使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范提交信息:
   `feat:`、`fix:`、`test:`、`docs:`、`chore:`、`refactor:`。
4. 任何行为变更都需要新增或更新测试。**没有测试的新特性通常不会被合并**。
5. 在请求评审前,确保 `uv run ruff check src tests && uv run pytest` 全部通过。

## 报告 Bug

使用 **Bug report** Issue 模板,包含:
- 复现步骤(curl 命令或前端操作流程)
- 期望行为 vs 实际行为
- 后端日志(设置 `LOG_LEVEL=DEBUG`)
- 操作系统、Python 版本、`uv --version`

## 特性请求

使用 **Feature request** 模板。描述用户故事,而不只是解决方案,关联所有相关 Issue。

## 行为准则

参与项目即表示你同意遵守 [Code of Conduct](.github/CODE_OF_CONDUCT.md)
(目前为占位文件 —— 在公开发布前应替换为 Contributor Covenant)。

## 许可证

提交贡献即表示你同意你的贡献以项目的 [MIT 许可证](LICENSE) 进行授权。
