/** Regression tests for storefront session requests and backend proxy routing. */
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const load = createRequire(import.meta.url);
const project = fileURLToPath(new URL("..", import.meta.url));
const build = mkdtempSync(join(tmpdir(), "eshop-session-tests-"));
const originalFetch = global.fetch;
const originalEnv = {
  API_BASE_URL: process.env.API_BASE_URL,
  NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE,
  NODE_ENV: process.env.NODE_ENV,
};
process.env.NEXT_PUBLIC_API_BASE = "https://eshop-hmdataset-production.up.railway.app";

const program = ts.createProgram({
  rootNames: [
    join(project, "src/lib/auth.ts"),
    join(project, "src/lib/orders.ts"),
    join(project, "src/lib/cartApi.ts"),
    join(project, "next.config.ts"),
  ],
  options: {
    target: ts.ScriptTarget.ES2020,
    module: ts.ModuleKind.CommonJS,
    moduleResolution: ts.ModuleResolutionKind.Node10,
    esModuleInterop: true,
    skipLibCheck: true,
    strict: true,
    rootDir: project,
    outDir: build,
  },
});
const emitted = program.emit();
const errors = ts.getPreEmitDiagnostics(program).concat(emitted.diagnostics);
assert.equal(errors.length, 0, ts.formatDiagnosticsWithColorAndContext(
  errors, ts.createCompilerHost(program.getCompilerOptions())
));

const auth = load(join(build, "src/lib/auth.js"));
const { getOrders } = load(join(build, "src/lib/orders.js"));
const { cartApi } = load(join(build, "src/lib/cartApi.js"));

/**
 * Install a fetch double that records URLs and cookie-related options.
 * Params: None.
 * Returns: The request array populated by calls to the API clients.
 */
function captureFetch() {
  const calls = [];
  global.fetch =
  /**
   * Record an API call and provide an empty successful JSON response.
   * Params: url: Request URL; options: Fetch options supplied by the client.
   * Returns: A promise resolving to a successful JSON response.
   */
  async function recordFetch(url, options) {
    calls.push({ url, options });
    return new Response("{}", {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };
  return calls;
}

/**
 * Check endpoint paths and require cookies and fresh responses for sessions.
 * Params: calls: Recorded fetch requests; paths: Expected backend endpoint paths.
 * Returns: Nothing; assertions fail for cross-site or cached session requests.
 */
function assertSessionRequests(calls, paths) {
  assert.deepEqual(
    calls.map(
      /** Read a request URL. Params: call: Recorded request. Returns: Its URL. */
      (call) => call.url
    ),
    paths.map(
      /** Prefix a backend path. Params: path: API endpoint. Returns: Proxy URL. */
      (path) => "/backend" + path
    )
  );
  for (const { options } of calls) {
    assert.equal(options.credentials, "include");
    assert.equal(options.cache, "no-store");
  }
}

/**
 * Verify registration, identity lookup, login, and logout stay on the storefront.
 * Params: None.
 * Returns: A promise resolving after all authentication requests are checked.
 */
async function testAuthProxy() {
  const calls = captureFetch();
  const email = "agent-demo@example.com";
  await auth.register({ email, name: "Agent Demo User" });
  await auth.me();
  await auth.login({ email, password: "" });
  await auth.logout();
  assertSessionRequests(calls, ["/auth/register", "/auth/me", "/auth/login", "/auth/logout"]);
  assert.deepEqual(JSON.parse(calls[0].options.body), { email, name: "Agent Demo User" });
}

/**
 * Verify account order history uses the same host as the login cookie.
 * Params: None.
 * Returns: A promise resolving after the order-history request is checked.
 */
async function testOrdersProxy() {
  const calls = captureFetch();
  await getOrders();
  assertSessionRequests(calls, ["/orders"]);
}

/**
 * Verify every cart operation shares the auth cookie and guest-cart cookie host.
 * Params: None.
 * Returns: A promise resolving after cart paths, methods, and bodies are checked.
 */
async function testCartProxy() {
  const calls = captureFetch();
  await cartApi.getCart();
  await cartApi.addItem("0493438021", 2);
  await cartApi.setQuantity("item-1", 3);
  await cartApi.removeItem("item-1");
  await cartApi.clear();
  await cartApi.checkout();
  assertSessionRequests(calls, [
    "/cart", "/cart/items", "/cart/items/item-1", "/cart/items/item-1", "/cart/clear", "/cart/checkout",
  ]);
  assert.deepEqual(calls.map(
    /** Read the effective HTTP method. Params: call: Request. Returns: Its method. */
    (call) => call.options.method || "GET"
  ), ["GET", "POST", "PATCH", "DELETE", "POST", "POST"]);
  assert.deepEqual(JSON.parse(calls[1].options.body), { product_id: "0493438021", quantity: 2 });
}

/**
 * Verify the proxy targets the configured backend and avoids recursive rewrites.
 * Params: None.
 * Returns: A promise resolving after server, development, and production targets are checked.
 */
async function testRewriteTargets() {
  const configPath = join(build, "next.config.js");
  const cases = [
    { server: "http://127.0.0.1:8001/", public: "https://unused.example.com", mode: "production", expected: "http://127.0.0.1:8001/:path*" },
    { server: "", public: "https://eshop-hmdataset-production.up.railway.app/", mode: "production", expected: "https://eshop-hmdataset-production.up.railway.app/:path*" },
    { server: "", public: "/backend", mode: "development", expected: "http://127.0.0.1:8000/:path*" },
    { server: "", public: "/backend", mode: "production", expected: "https://eshop-hmdataset-production.up.railway.app/:path*" },
  ];
  for (const entry of cases) {
    process.env.API_BASE_URL = entry.server;
    process.env.NEXT_PUBLIC_API_BASE = entry.public;
    process.env.NODE_ENV = entry.mode;
    delete load.cache[configPath];
    const config = load(configPath).default;
    assert.deepEqual(await config.rewrites(), [{ source: "/backend/:path*", destination: entry.expected }]);
  }
}

/**
 * Verify rejected authentication stays visible to the caller.
 * Params: None.
 * Returns: A promise resolving after an unauthorized session lookup is rejected.
 */
async function testUnauthorizedResponse() {
  global.fetch =
  /**
   * Return the unauthorized response used by the negative session test.
   * Params: None.
   * Returns: A promise resolving to an HTTP 401 response.
   */
  async function rejectSession() {
    return new Response('{"detail":"Not authenticated"}', { status: 401 });
  };
  await assert.rejects(auth.me(), /Not authenticated/);
}

/**
 * Restore process state and remove only this suite's generated build files.
 * Params: None.
 * Returns: Nothing.
 */
function cleanup() {
  global.fetch = originalFetch;
  for (const [key, value] of Object.entries(originalEnv)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  rmSync(build, { recursive: true, force: true });
}

test("authentication uses the same-origin cookie proxy", testAuthProxy);
test("order history uses the same-origin cookie proxy", testOrdersProxy);
test("all cart operations use the same-origin cookie proxy", testCartProxy);
test("backend rewrites honor the deployment and local configuration", testRewriteTargets);
test("unauthorized sessions remain errors", testUnauthorizedResponse);
after(cleanup);
