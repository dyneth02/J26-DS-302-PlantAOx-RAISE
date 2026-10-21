import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MlflowLauncher } from "@/features/c2-pu/components/MlflowLauncher";

describe("MlflowLauncher", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("opens MLflow in a new tab when it is reachable", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response()) as unknown as typeof fetch;
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<MlflowLauncher />);
    fireEvent.click(screen.getByRole("button", { name: /open mlflow ui/i }));

    await waitFor(() => expect(openSpy).toHaveBeenCalledWith("http://127.0.0.1:5003", "_blank", "noopener"));
    expect(screen.queryByText(/isn't running/i)).not.toBeInTheDocument();
  });

  it("shows the start command when MLflow is unreachable, and lets the user copy it", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch")) as unknown as typeof fetch;
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(<MlflowLauncher />);
    fireEvent.click(screen.getByRole("button", { name: /open mlflow ui/i }));

    expect(await screen.findByText(/isn't running on http:\/\/127\.0\.0\.1:5003/i)).toBeInTheDocument();
    expect(screen.getByText(/mlflow_tracking\\\.venv\\Scripts\\mlflow\.exe/)).toBeInTheDocument();
    expect(openSpy).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /copy command/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining("--port 5003")));
  });
});
