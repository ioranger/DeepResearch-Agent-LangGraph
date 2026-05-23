"""
工具函数模块 - 提供深度研究服务中跨模块共享的通用辅助函数。

本模块包含：
- 配置值解析
- 模型输出清洗（去除思考标记）
- 搜索结果去重与格式化
- 来源信息汇总
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

# 每个 token 大约对应 4 个字符（用于估算 token 数量与字符数之间的转换）
CHARS_PER_TOKEN = 4

# 模块级别的日志记录器
logger = logging.getLogger(__name__)


def get_config_value(value: Any) -> str:
    """获取配置值的字符串表示。

    当配置值是枚举类型（Enum）时，取其 .value 属性；
    若本身已经是字符串，则直接返回。

    Args:
        value: 配置项的值，可能是字符串或枚举类型

    Returns:
        配置值的纯字符串形式
    """
    return value if isinstance(value, str) else value.value


def strip_thinking_tokens(text: str) -> str:
    """移除模型响应中的 <think>...</think> 思考标记段落。

    部分 LLM（如 DeepSeek）会在输出中包含 <think> 标签包裹的内部推理过程，
    这些内容不应展示给最终用户。本函数会循环查找并移除所有此类标记。

    Args:
        text: 模型的原始响应文本

    Returns:
        去除所有思考标记后的干净文本
    """
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text


def deduplicate_and_format_sources(
    search_response: Dict[str, Any] | List[Dict[str, Any]],
    max_tokens_per_source: int,
    *,
    fetch_full_page: bool = False,
) -> str:
    """对搜索结果进行去重并格式化为可供 LLM 使用的文本上下文。

    该函数是搜索结果预处理的核心步骤：
    1. 统一处理字典格式和列表格式的搜索响应
    2. 根据 URL 进行去重，确保同一来源不会重复出现
    3. 将每条来源格式化为包含标题、URL、内容的结构化文本
    4. 可选地包含完整页面内容（按 token 限制截断）

    Args:
        search_response: 搜索 API 返回的结果，支持两种格式：
            - 字典格式：{"results": [{"url": ..., "title": ..., "content": ...}, ...]}
            - 列表格式：[{"url": ..., "title": ..., "content": ...}, ...]
        max_tokens_per_source: 每条来源的完整内容最大 token 数限制
        fetch_full_page: 是否包含完整页面的原始内容（raw_content 字段）

    Returns:
        格式化后的文本字符串，包含所有去重后来源的信息，
        可直接嵌入到 LLM 的 prompt 中作为参考上下文
    """
    # 统一将输入转换为来源列表
    if isinstance(search_response, dict):
        sources_list = search_response.get("results", [])
    else:
        sources_list = search_response

    # 使用字典按 URL 去重，保留首次出现的来源
    unique_sources: dict[str, Dict[str, Any]] = {}
    for source in sources_list:
        url = source.get("url")
        if not url:
            continue
        if url not in unique_sources:
            unique_sources[url] = source

    # 逐条格式化来源信息
    formatted_parts: List[str] = []
    for source in unique_sources.values():
        title = source.get("title") or source.get("url", "")
        content = source.get("content", "")
        formatted_parts.append(f"信息来源: {title}\n\n")
        formatted_parts.append(f"URL: {source.get('url', '')}\n\n")
        formatted_parts.append(f"信息内容: {content}\n\n")

        # 如果需要包含完整页面内容，则按 token 限制截断
        if fetch_full_page:
            raw_content = source.get("raw_content")
            if raw_content is None:
                logger.debug("raw_content missing for %s", source.get("url", ""))
                raw_content = ""
            # 将 token 数量转换为字符数量进行截断
            char_limit = max_tokens_per_source * CHARS_PER_TOKEN
            if len(raw_content) > char_limit:
                raw_content = f"{raw_content[:char_limit]}... [truncated]"
            formatted_parts.append(
                f"详细信息内容限制为 {max_tokens_per_source} 个 token: {raw_content}\n\n"
            )

    return "".join(formatted_parts).strip()


def format_sources(search_results: Dict[str, Any] | None) -> str:
    """将搜索结果格式化为 Markdown 无序列表形式的来源摘要。

    用于在最终报告中列出参考来源清单，每条来源以
    "* 标题 : URL" 的格式呈现。

    Args:
        search_results: 搜索 API 返回的结果字典，格式为
            {"results": [{"url": ..., "title": ...}, ...]}
            如果为 None 或空字典则返回空字符串

    Returns:
        Markdown 格式的来源列表字符串，例如：
        * 文章标题1 : https://example.com/1
        * 文章标题2 : https://example.com/2
    """
    if not search_results:
        return ""

    results = search_results.get("results", [])
    return "\n".join(
        f"* {item.get('title', item.get('url', ''))} : {item.get('url', '')}"
        for item in results
        if item.get("url")
    )
