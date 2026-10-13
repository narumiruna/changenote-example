import assert from "node:assert/strict";
import test from "node:test";
import { hello } from "./index.js";

test("hello returns a greeting", () => {
  assert.equal(hello(), "Hello from pkg-node!");
});
