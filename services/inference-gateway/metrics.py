from __future__ import annotations

from collections import Counter, deque

from models import MetricsResponse, MetricsSummary, RequestMetric


def _avg(values: list[float | int | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 3)


class RollingMetricsStore:
    def __init__(self, capacity: int = 1000) -> None:
        self.capacity = capacity
        self._metrics: deque[RequestMetric] = deque(maxlen=capacity)

    def record(self, metric: RequestMetric) -> None:
        self._metrics.append(metric)

    def summary(self) -> MetricsResponse:
        by_model: dict[str, list[RequestMetric]] = {}
        for metric in self._metrics:
            by_model.setdefault(metric.model, []).append(metric)

        models = {
            model: MetricsSummary(
                count=len(items),
                avg_input_tokens=_avg([item.input_tokens for item in items]),
                avg_output_tokens=_avg([item.output_tokens for item in items]),
                avg_time_to_first_token_ms=_avg([item.time_to_first_token_ms for item in items]),
                avg_total_latency_ms=_avg([item.latency_ms for item in items]),
                avg_tokens_per_second=_avg([item.tokens_per_second for item in items]),
            )
            for model, items in by_model.items()
        }

        endpoint_counts = Counter(metric.endpoint for metric in self._metrics)
        return MetricsResponse(
            models=models,
            recent_requests=len(self._metrics),
            by_endpoint=dict(endpoint_counts),
            raw=[metric.model_dump() for metric in self._metrics],
        )
