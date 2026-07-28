import { NextResponse } from "next/server";

import { validateBrowserAuditRequest } from "../../../lib/browser-audit";
import { runBrowserAudit } from "../../../lib/server-audit";

export const runtime = "nodejs";
export const maxDuration = 300;
const MAX_BODY_BYTES = 16_384;

export async function POST(request: Request) {
  try {
    const length = Number(request.headers.get("content-length") ?? 0);
    if (length > MAX_BODY_BYTES) {
      return NextResponse.json({ error: "Request body is too large." }, { status: 413 });
    }
    const rawBody = await request.text();
    if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
      return NextResponse.json({ error: "Request body is too large." }, { status: 413 });
    }
    const input = validateBrowserAuditRequest(JSON.parse(rawBody));
    const report = await runBrowserAudit(input, request.signal);
    return NextResponse.json(report, {
      headers: {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "The audit could not be completed.";
    return NextResponse.json(
      { error: message },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
}
