"""Loopback-only smoke checks for the real production-shaped container stack."""

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit

import httpx
from websockets.sync.client import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5182")
    parser.add_argument("--origin", default="https://portfolio.local.invalid")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--state", type=Path, default=Path(".local/portfolio-smoke-session.json"))
    parser.add_argument("--report", type=Path, default=Path(".local/portfolio-stack-result.json"))
    args = parser.parse_args()
    if urlsplit(args.url).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("This smoke test is restricted to a loopback-bound stack")
    def client(ip):
        return httpx.Client(base_url=args.url, headers={"Origin": args.origin, "X-Forwarded-For": ip}, timeout=10, trust_env=False)
    def require(response, status=200):
        assert response.status_code == status, f"Unexpected HTTP status {response.status_code}"
        return response.json() if response.content else None
    def attach(c):
        c.headers["Cookie"] = "; ".join(f"{item.name}={item.value}" for item in c.cookies.jar)
    if args.resume:
        state = json.loads(args.state.read_text())
        c = client("198.51.100.11")
        c.headers["Cookie"] = state["cookie"]
        actual = require(c.get(state["prefix"] + "/snapshot"))
        assert [message["id"] for message in actual["messages"]] == state["message_ids"]
        print(json.dumps({"restart_persistence": "passed", "persisted_messages": len(actual["messages"])}))
        return
    c = client("198.51.100.11")
    caps = require(c.get("/api/v1/public/capabilities"))
    assert caps == {"demo_available": True, "ai_mode": "simulated"}
    identity = require(c.post("/api/v1/public/demo")); attach(c)
    assert identity["fictional_data"] and identity["provider_mode"] == "fake"
    assert all(item.secure for item in c.cookies.jar)
    c.headers["X-CSRF-Token"] = identity["csrf_token"]
    staff = require(c.get("/api/v1/auth/staff/me"))
    wid = identity["workspace_id"]
    assert staff["memberships"][0]["workspace_id"] == wid
    conversation = require(c.post("/api/v1/customer/conversations", headers={"Idempotency-Key": str(uuid4())}))
    cid = conversation["id"]; prefix = f"/api/v1/customer/conversations/{cid}"
    message = {"client_message_id": str(uuid4()), "body": "How long is the Tarvio trial?"}
    require(c.post(prefix + "/messages", json=message), 201)
    require(c.post(prefix + "/messages", json=message))
    deadline = time.monotonic() + 45
    while True:
        snapshot = require(c.get(prefix + "/snapshot"))
        if any(item["sender_kind"] == "assistant" for item in snapshot["messages"]): break
        if time.monotonic() >= deadline: raise RuntimeError("Assistant did not finish through the real worker")
        time.sleep(0.2)
    assert len(snapshot["messages"]) == 2
    answer = snapshot["messages"][-1]
    assert "[S1]" in answer["body"]
    citation = require(c.get(prefix + f"/citations/{answer['id']}/S1"))
    assert citation["available"] and "fourteen days" in citation["excerpt"]
    current = require(c.post(prefix + "/handoff", headers={"Idempotency-Key": str(uuid4())}, json={"expected_state_version": snapshot["conversation"]["state_version"]}))
    staff_prefix = f"/api/v1/staff/workspaces/{wid}/conversations/{cid}"
    staff_headers = {"X-CSRF-Token": staff["csrf_token"], "Idempotency-Key": str(uuid4())}
    current = require(c.post(staff_prefix + "/claim", headers=staff_headers, json={"expected_state_version": current["state_version"]}))
    require(c.post(staff_prefix + "/messages", headers=staff_headers, json={"client_message_id": str(uuid4()), "body": "پاسخ واقعی کارشناس در بررسی کانتینر"}), 201)
    current = require(c.post(staff_prefix + "/resolve", headers={**staff_headers, "Idempotency-Key": str(uuid4())}, json={"expected_state_version": current["state_version"]}))
    require(c.post(prefix + "/reopen", headers={"Idempotency-Key": str(uuid4())}, json={"expected_state_version": current["state_version"]}))
    docs = f"/api/v1/staff/workspaces/{wid}/knowledge/documents"
    uploaded = require(c.post(docs, headers={**staff_headers, "Idempotency-Key": str(uuid4())}, data={"title": "Fictional container verification"}, files={"file": ("portfolio.md", b"# Fictional portfolio policy\nTarvio Cloud demo is fictional.", "text/markdown")}), 202)
    deadline = time.monotonic() + 45
    while True:
        documents = require(c.get(docs))
        document = next(item for item in documents if item["id"] == uploaded["document_id"])
        if document["active_version_id"] == uploaded["version_id"]: break
        if time.monotonic() > deadline: raise RuntimeError("Document processing did not finish")
        time.sleep(0.2)
    require(c.delete(docs + "/" + document["id"], headers=staff_headers), 204)
    snapshot = require(c.get(prefix + "/snapshot"))
    ws_url = args.url.replace("http://", "ws://") + "/api/v1/realtime/customer"
    seqs = []
    with connect(ws_url, origin=args.origin, additional_headers={"Cookie": c.headers["Cookie"]}, open_timeout=5) as socket:
        socket.send(json.dumps({"protocol_version": 1, "type": "subscribe", "conversation_id": cid, "after_seq": 0}))
        while not seqs or seqs[-1] < snapshot["event_cursor"]:
            frame = json.loads(socket.recv(timeout=10))
            if frame.get("type") == "ping": socket.send(json.dumps({"protocol_version": 1, "type": "pong"}))
            if "seq" in frame: seqs.append(frame["seq"])
    assert seqs == list(range(1, snapshot["event_cursor"] + 1))
    assert "تارویو" in c.get(f"/app/{wid}/conversations/{cid}").text
    # The gateway must preserve distinct visitors and ignore caller spoofing elsewhere.
    others = []
    try:
        for _ in range(4):
            other = client("198.51.100.11"); others.append(other)
            require(other.post("/api/v1/public/demo"))
        other = client("198.51.100.11"); others.append(other)
        require(other.post("/api/v1/public/demo"), 429)
        other = client("198.51.100.12"); others.append(other)
        require(other.post("/api/v1/public/demo"))
    finally:
        for other in others: other.close()
    state = {"prefix": prefix, "cookie": c.headers["Cookie"], "message_ids": [message["id"] for message in snapshot["messages"]]}
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state)); args.state.chmod(0o600)
    report = {"mode": "real isolated production-shaped stack; explicit fake LLM", "http_origin_simulation": "Secure cookie flags and exact HTTPS Origin validated over a loopback HTTP transport; public TLS not verified", "customer_staff_messaging": "passed", "single_message_retry": "passed", "assistant_citation": "passed", "handoff_claim_resolve_reopen": "passed", "ingestion_withdrawal": "passed", "caddy_websocket_replay": {"events": len(seqs), "ordered": True}, "distinct_proxy_rate_buckets": "passed", "persisted_messages": len(snapshot["messages"])}
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    c.close()


if __name__ == "__main__": main()
