import { describe, expect, it } from "vitest";

import { validateBrowserAuditRequest, type BrowserAuditRequest } from "../lib/browser-audit";
import { runBrowserAudit, TIME_BUDGET_MS } from "../lib/server-audit";
import { verifyV2Report } from "../lib/v2-hash";

const KEY = "sk-test-key-never-in-report";

/** MMLU-shaped rows; every correct answer is option 0 so a position-bound model scores 100%. */
function rows(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    row_idx: index,
    row: { question: `What is ${index} + 1?`, choices: [String(index + 1), String(index + 2), String(index + 3), String(index + 4)], answer: 0, subject: "math" },
  }));
}

type Model = (prompt: string, body: Record<string, unknown>) => string | { status: number };

/** Answers by content: finds the label whose text is the true sum. */
const contentModel: Model = (prompt) => {
  const match = prompt.match(/What is (\d+) \+ 1\?/);
  const answer = String(Number(match![1]) + 1);
  const line = prompt.split("\n").find((entry) => new RegExp(`^\\(?([a-z])[.)] ${answer}$`).test(entry));
  return `The answer is ${line!.match(/^\(?([a-z])/)![1]}`;
};
/** Always answers "a" — the canonical position of the key in this fixture. */
const positionModel: Model = () => "a";

function fakeFetch(model: Model, count: number, seen: Array<Record<string, unknown>> = []) {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.startsWith("https://datasets-server.huggingface.co/rows")) return Response.json({ rows: rows(count) });
    if (url.startsWith("https://huggingface.co/api/datasets/")) return Response.json({ sha: "pinned-sha" });
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    seen.push({ url, body, headers: init?.headers });
    const prompt = String((body.messages as Array<{ content: unknown }>)[0]!.content);
    const reply = model(prompt, body);
    if (typeof reply !== "string") return Response.json({ error: { message: "nope" } }, { status: reply.status });
    return Response.json({
      id: "x",
      object: "chat.completion",
      created: 0,
      model: String(body.model),
      choices: [{ index: 0, message: { role: "assistant", content: reply }, finish_reason: "stop" }],
      usage: { prompt_tokens: 10, completion_tokens: 2, total_tokens: 12 },
    });
  }) as typeof fetch;
}

const request = (overrides: Partial<BrowserAuditRequest> = {}): BrowserAuditRequest =>
  validateBrowserAuditRequest({ provider: "together", apiKey: KEY, model: "test/model", benchmark: "mmlu", itemCount: 12, offset: 0, acknowledgeExternalTransfer: true, ...overrides });

const finding = (report: Awaited<ReturnType<typeof runBrowserAudit>>, id: string) => report.findings.find((entry) => entry.detector_id === id)!;
let clock = 0;
const deps = (model: Model, count = 12, seen?: Array<Record<string, unknown>>) => ({ fetch: fakeFetch(model, count, seen), now: () => clock });

describe("hosted browser audit (mocked provider + dataset host)", () => {
  it("finds no dependence for a content-tracking model and signs a verifiable report", async () => {
    const report = await runBrowserAudit(request(), undefined, deps(contentModel));
    expect(report.score.canonical_reproduced_score).toBe(1);
    expect(report.score.robust_score).toBe(1);
    expect(finding(report, "option_order").direction).toBe("contradicts");
    expect(report.responses).toHaveLength(36);
    expect((await verifyV2Report(JSON.parse(JSON.stringify(report)))).ok).toBe(true);
    expect(JSON.stringify(report)).not.toContain(KEY);
    expect(report.benchmark.version).toBe("pinned-sha");
  });

  it("flags answer-position dependence for a position-bound model", async () => {
    const report = await runBrowserAudit(request(), undefined, deps(positionModel));
    expect(report.score.canonical_reproduced_score).toBe(1);
    expect(finding(report, "option_order")).toMatchObject({ direction: "supports", effect_size: 1 });
    expect(finding(report, "template_dependence").direction).toBe("contradicts");
    const row = report.evidence_matrix.find((entry) => entry.hypothesis === "answer-position dependence")!;
    expect(row.supporting).toEqual(["option_order"]);
  });

  it("excludes failed requests instead of scoring them wrong", async () => {
    const flaky: Model = (prompt, body) => (prompt.startsWith("Question:") ? { status: 400 } : contentModel(prompt, body));
    const report = await runBrowserAudit(request(), undefined, deps(flaky));
    expect(report.score.robust_score).toBe(1);
    expect(finding(report, "template_dependence").status).toBe("not_run");
    expect(report.limitations.some((note) => note.includes("12 request(s) failed"))).toBe(true);
  });

  it("surfaces a clear error when every request is rejected", async () => {
    await expect(runBrowserAudit(request(), undefined, deps(() => ({ status: 401 })))).rejects.toThrow("Provider rejected the key (HTTP 401)");
  });

  it("uses max_completion_tokens for OpenAI and drops temperature for reasoning models", async () => {
    const seen: Array<Record<string, unknown>> = [];
    await runBrowserAudit(request({ provider: "openai", model: "o3-mini", itemCount: 1 }), undefined, deps(contentModel, 1, seen));
    const body = seen[0]!.body as Record<string, unknown>;
    expect(seen[0]!.url).toBe("https://api.openai.com/v1/chat/completions");
    expect(body.max_completion_tokens).toBe(1024);
    expect(body).not.toHaveProperty("max_tokens");
    expect(body).not.toHaveProperty("temperature");
  });

  it("returns a partial report instead of timing out", async () => {
    let calls = 0;
    const slowClock = { fetch: fakeFetch(contentModel, 12), now: () => (calls++ > 40 ? TIME_BUDGET_MS + 1 : 0) };
    const report = await runBrowserAudit(request(), undefined, slowClock);
    expect(report.responses.some((response) => response.finish_reason === "skipped")).toBe(true);
    expect(report.limitations.some((note) => note.includes("excluded from scoring"))).toBe(true);
  });
});

describe("benchmark host failures", () => {
  it("names the dataset host when it is unreachable", async () => {
    const offline = (async () => {
      throw new TypeError("fetch failed");
    }) as typeof fetch;
    await expect(runBrowserAudit(request(), undefined, { fetch: offline, now: () => 0 })).rejects.toThrow("Could not reach the benchmark host");
  });
});
