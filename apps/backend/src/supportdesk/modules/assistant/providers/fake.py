import time
from collections.abc import Iterator

from supportdesk.config import get_settings
from supportdesk.modules.assistant.providers.base import Delta, ProviderFailure


class FakeProvider:
    def stream(
        self, messages: list[dict[str, str]], context_limit: int
    ) -> Iterator[Delta]:
        scenario = get_settings().fake_scenario
        if scenario in {"timeout", "429"}:
            raise ProviderFailure(
                "PROVIDER_TIMEOUT"
                if scenario == "timeout"
                else "PROVIDER_RATE_LIMITED",
                retryable=True,
            )
        question = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        ).casefold()
        forbidden = [
            "ignore",
            "نادیده",
            "hidden",
            "another workspace",
            "administrator command",
        ]
        supported = [
            "trial",
            "آزمایشی",
            "reset",
            "بازنشانی",
            "password",
            "رمز",
            "api key",
            "کوکی",
            "export",
            "خروجی",
            "support",
            "پشتیبانی",
            "webhook",
            "وب",
            "بازپرداخت نیاز",
            "کدام منطقه",
        ]
        if any(word in question for word in forbidden) or not any(
            word in question for word in supported
        ):
            yield Delta(text="NO_ANSWER", input_tokens=0, output_tokens=0)
            return
        source = messages[1]["content"].split("\n", 1)[-1]
        # This is an explicit fixture excerpt, never presented as a live model answer.
        answer = "پاسخ نمایشی بر پایهٔ سند: " + source[:900] + " [S1]"
        if scenario == "invalid_citation":
            answer = "پاسخ آزمایشی با ارجاع نامعتبر [S99]"
        for index in range(0, len(answer), 24):
            if scenario == "drop" and index >= 48:
                raise ProviderFailure("PROVIDER_STREAM_DROPPED", retryable=True)
            time.sleep(0.15 if scenario == "slow" else 0.01)
            yield Delta(text=answer[index : index + 24])
        yield Delta(
            input_tokens=sum(len(m["content"].encode()) for m in messages),
            output_tokens=len(answer.encode()),
        )
