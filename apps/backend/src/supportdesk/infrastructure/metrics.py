from prometheus_client import Counter, Gauge, Histogram

http_requests = Counter(
    "supportdesk_http_requests_total",
    "HTTP requests by bounded route template",
    ["method", "route", "status"],
)
http_latency = Histogram(
    "supportdesk_http_request_seconds",
    "HTTP latency by route template",
    ["method", "route"],
)
open_sockets = Gauge("supportdesk_open_sockets", "Open sockets in this API process")
