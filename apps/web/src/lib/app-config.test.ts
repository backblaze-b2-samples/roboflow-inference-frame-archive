import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the app name and description", () => {
    expect(APP_NAME).toBe("Roboflow Frame Archive");
    expect(APP_DESCRIPTION).toBe(
      "Edge inference frame + prediction archive on Backblaze B2"
    );
  });
});
