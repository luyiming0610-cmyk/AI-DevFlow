
import os

from openai import OpenAI


class ModelClient:
    """
    Unified model client for AI DevFlow.

    Modes:
        mock: local simulation, no API cost
        api: real DeepSeek API request
    """

    def __init__(self):
        self.mode = os.getenv(
            "AI_MODE", "mock"
        ).strip().lower()

        self.model = os.getenv(
            "AI_MODEL", "deepseek-flash"
        )

        self.base_url = os.getenv(
            "AI_BASE_URL",
            "https://api.deepseek.com"
        )

        self.client = None
        self.last_usage = None

        if self.mode not in ("mock", "api"):
            raise ValueError(
                "AI_MODE must be 'mock' or 'api'"
            )

        if self.mode == "api":
            api_key = os.getenv("AI_API_KEY")

            if not api_key:
                raise ValueError(
                    "AI_API_KEY is missing in .env"
                )

            self.client = OpenAI(
                api_key=api_key,
                base_url=self.base_url,
                timeout=45.0,
                max_retries=0,
            )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 3200,
    ) -> str:
        """
        Generate text from the configured model.
        """

        # MOCK mode never calls the API.
        if self.mode == "mock":
            self.last_usage = None

            return (
                "# MOCK Development Plan\n\n"
                "This is a simulated response, "
                "not AI-generated.\n\n"
                "1. Parse event upload logs.\n"
                "2. Count success and failure records.\n"
                "3. Handle malformed input safely.\n"
                "4. Write pytest tests.\n"
                "5. Produce JSON and Markdown reports.\n"
            )

        # Actual DeepSeek request.
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            max_tokens=max_tokens,
            extra_body={
                "thinking": {
                    "type": "disabled"
                }
            },
        )

        if not response.choices:
            raise RuntimeError(
                "API returned no response choices"
            )

        choice = response.choices[0]
        content = choice.message.content
        finish_reason = choice.finish_reason

        usage = response.usage

        if usage is not None:
            self.last_usage = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

            print(
                "[API Usage] "
                f"Input: {usage.prompt_tokens}, "
                f"Output: {usage.completion_tokens}, "
                f"Total: {usage.total_tokens}"
            )

        if finish_reason == "length":
            raise RuntimeError(
                "Model output reached max_tokens. "
                f"Usage: {self.last_usage}"
            )

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Model returned empty content. "
                f"finish_reason={finish_reason}, "
                f"usage={self.last_usage}"
            )

        return content.strip()
