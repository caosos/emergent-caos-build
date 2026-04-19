import tiktoken


MODEL_FALLBACKS = {
    "gpt-5": "gpt-4o",
    "gpt-5.2": "gpt-4o",
}


def _encoding_for_model(model: str):
    for candidate in (model, MODEL_FALLBACKS.get(model), "gpt-4o"):
        if not candidate:
            continue
        try:
            return tiktoken.encoding_for_model(candidate)
        except KeyError:
            continue
    return tiktoken.get_encoding("o200k_base")


def count_text_tokens(text: str, model: str) -> int:
    if not text:
        return 0
    return len(_encoding_for_model(model).encode(text))


def extract_usage_payload(response) -> dict:
    usage = getattr(response, "usage", None)
    if not usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "token_source": "local_tokenizer_fallback"}
    payload = usage if isinstance(usage, dict) else usage.dict()
    return {
        "prompt_tokens": payload.get("prompt_tokens") or payload.get("input_tokens") or 0,
        "completion_tokens": payload.get("completion_tokens") or payload.get("output_tokens") or 0,
        "total_tokens": payload.get("total_tokens") or 0,
        "token_source": "provider_usage",
    }


def build_token_receipt(
    model: str,
    prompt_sections: dict,
    system_prompt: str,
    user_text: str,
    assistant_text: str,
    response,
    prior_prompt_total: int = 0,
    prior_completion_total: int = 0,
) -> dict:
    history_tokens = count_text_tokens(prompt_sections.get("history_block", ""), model)
    memory_tokens = count_text_tokens(prompt_sections.get("memory_block", ""), model)
    continuity_tokens = count_text_tokens(prompt_sections.get("continuity_block", ""), model)
    system_prompt_tokens = count_text_tokens(system_prompt, model)
    user_message_tokens = count_text_tokens(user_text, model)
    assistant_reply_tokens = count_text_tokens(assistant_text, model)
    usage = extract_usage_payload(response)
    prompt_tokens = usage["prompt_tokens"] or (system_prompt_tokens + user_message_tokens)
    completion_tokens = usage["completion_tokens"] or assistant_reply_tokens
    total_tokens = usage["total_tokens"] or (prompt_tokens + completion_tokens)
    session_prompt_tokens_total = prior_prompt_total + prompt_tokens
    session_completion_tokens_total = prior_completion_total + completion_tokens
    return {
        "token_source": usage["token_source"],
        "history_tokens": history_tokens,
        "memory_tokens": memory_tokens,
        "continuity_tokens": continuity_tokens,
        "active_context_tokens": history_tokens + memory_tokens + continuity_tokens,
        "system_prompt_tokens": system_prompt_tokens,
        "user_message_tokens": user_message_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "session_prompt_tokens_total": session_prompt_tokens_total,
        "session_completion_tokens_total": session_completion_tokens_total,
        "session_total_tokens": session_prompt_tokens_total + session_completion_tokens_total,
    }