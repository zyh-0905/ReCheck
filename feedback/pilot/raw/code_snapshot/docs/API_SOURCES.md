# Interface references

Reviewed 2026-09-12. These sources support the request/response shape, not compatibility with every provider and not any model research result.

- OpenAI official Chat Completions reference: https://developers.openai.com/api/reference/resources/chat
- OpenAI official create endpoint reference: https://platform.openai.com/docs/api-reference/chat/create
- Response fields used: choices[0].message.content, finish_reason, model, usage.prompt_tokens, usage.completion_tokens, usage.prompt_tokens_details.cached_tokens.
- max_completion_tokens includes reasoning and visible output in supported OpenAI models; max_tokens compatibility varies by model and serving platform. This kit does not silently switch these parameters.

No closed API was invoked in the implementation environment. Local test server responses are test fixtures and labelled as such.
