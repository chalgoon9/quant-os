import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./api";

describe("resolveApiBaseUrl", () => {
  it("uses the current browser host by default", () => {
    const url = resolveApiBaseUrl({
      envApiBaseUrl: undefined,
      protocol: "http:",
      hostname: "192.168.0.31",
    });

    expect(url).toBe("http://192.168.0.31:8000/api");
  });

  it("prefers explicit env override when provided", () => {
    const url = resolveApiBaseUrl({
      envApiBaseUrl: "http://10.0.0.5:9000/api/",
      protocol: "http:",
      hostname: "192.168.0.31",
    });

    expect(url).toBe("http://10.0.0.5:9000/api");
  });
});
