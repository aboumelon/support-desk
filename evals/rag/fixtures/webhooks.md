# Fictional Naran Cloud webhooks
A workspace administrator creates a webhook in Settings, Integrations, Webhooks. HTTPS endpoints are required.
The webhook secret signs request bodies with HMAC-SHA256 in the X-Naran-Signature header. Compare signatures using a constant-time comparison.
The fictional service retries failed webhook deliveries after 10 seconds, 60 seconds, and 5 minutes, for four total delivery attempts including the original attempt.
وب‌هوک از تنظیمات، یکپارچه‌سازی و وب‌هوک ساخته می‌شود. آدرس باید HTTPS باشد. امضا از HMAC-SHA256 استفاده می‌کند.
