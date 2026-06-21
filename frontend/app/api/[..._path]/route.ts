import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const TARGET = process.env.BACKEND_URL_INTERNAL ?? "http://backend:8000";

async function proxy(request: NextRequest, params: { _path?: string[] }) {
  const path = (params._path ?? []).join("/");
  // The catch-all sits under /api/, so _path is ["v1","threads"] for a request
  // to /api/v1/threads. Re-prepend "api/" so the backend receives its full path.
  const url = new URL(`${TARGET}/api/${path}`);
  url.search = request.nextUrl.search;

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unreachable";
    return new NextResponse(JSON.stringify({ error: message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }

  // For SSE / streaming responses, pipe the body directly instead of buffering
  // with response.text() — buffering causes the entire stream to arrive at once
  // instead of token-by-token, breaking live streaming in the UI.
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/event-stream") || contentType.includes("octet-stream")) {
    const headers = new Headers(response.headers);
    // Ensure browser does not buffer the SSE stream
    headers.set("Content-Type", "text/event-stream");
    headers.set("Cache-Control", "no-cache, no-transform");
    headers.set("X-Accel-Buffering", "no");
    return new NextResponse(response.body, {
      status: response.status,
      headers,
    });
  }

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: response.headers,
  });
}

export async function GET(request: NextRequest, ctx: { params: Promise<{ _path?: string[] }> }) {
  return proxy(request, await ctx.params);
}

export async function POST(request: NextRequest, ctx: { params: Promise<{ _path?: string[] }> }) {
  return proxy(request, await ctx.params);
}

export async function PUT(request: NextRequest, ctx: { params: Promise<{ _path?: string[] }> }) {
  return proxy(request, await ctx.params);
}

export async function PATCH(request: NextRequest, ctx: { params: Promise<{ _path?: string[] }> }) {
  return proxy(request, await ctx.params);
}

export async function DELETE(request: NextRequest, ctx: { params: Promise<{ _path?: string[] }> }) {
  return proxy(request, await ctx.params);
}

export async function OPTIONS(request: NextRequest, ctx: { params: Promise<{ _path?: string[] }> }) {
  return proxy(request, await ctx.params);
}
