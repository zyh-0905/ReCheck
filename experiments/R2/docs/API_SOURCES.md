# 接口与来源记录（2026-09-12）
1. 原始LLM_Pilot_Kit_v0.1、R1审查及两次用户反馈是本轮代码与回归样例依据。
   SHA-256见PROVENANCE.json。旧源文件保留，原ZIP不改写。
2. DeepSeek官方 Thinking Mode：
   https://api-docs.deepseek.com/guides/thinking_mode/
   官方接口格式说明thinking enabled/disabled、reasoning_effort等字段。
   Chat Completions：
   https://api-docs.deepseek.com/api/create-chat-completion/
   usage可以提供prompt_cache_hit_tokens/prompt_cache_miss_tokens；
   本包同时检查通用cached_tokens路径，并把冲突标为unknown。
3. 本轮直接打开官方页面出现超时；搜索索引返回的型号/价格版本并不都与用户最新日志一致。
   因此不沿用搜索缓存的价目、不重新命名用户已测可用模型、不独立认证权重版本。
   模式参数仅采用官方文档的格式，兼容性由用户一次smoke确定；失败即停。
4. 当前配置沿用反馈端点和模型ID，但新增显式thinking enabled/high。
   真实调用、usage、身份字段和截断需要用户运行后审查；研究端本轮无新远端LLM请求。
5. 没有外部预注册、人工同行审查、AppWorld/MemoryArena结果或新的论文录用判断。
