import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const TARGET = process.env.BACKEND_URL_INTERNAL ?? "http://backend:8000";

async function proxy(request: NextRequest, params: { _path?: string[] }) {
  const path = (params._path ?? []).join("/");
  const url = new URL(`${TARGET}/${path}`);
  url.search = request.nextUrl.search;

  const response = await fetch(url.toString(), {
    method: request.method,
    headers: request.headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
  });

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
