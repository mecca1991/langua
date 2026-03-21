import { describe, it, expect } from "vitest";
import { config } from "./config";

describe("config", () => {
  it("exposes API URL", () => {
    expect(config.apiUrl).toBeDefined();
    expect(typeof config.apiUrl).toBe("string");
  });

  it("exposes Supabase URL", () => {
    expect(config.supabaseUrl).toBeDefined();
    expect(typeof config.supabaseUrl).toBe("string");
  });

  it("exposes Supabase anon key", () => {
    expect(config.supabaseAnonKey).toBeDefined();
    expect(typeof config.supabaseAnonKey).toBe("string");
  });
});
