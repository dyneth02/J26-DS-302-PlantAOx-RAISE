import { useEffect, useRef, useState, type DependencyList } from "react";

export type ApiState<T> =
  | { status: "loading" }
  | { status: "error"; error: Error }
  | { status: "success"; data: T };

/** Shared GET-state hook used by component pages; callers control refetch dependencies. */
export function useApi<T>(request: () => Promise<T>, dependencies: DependencyList = []): ApiState<T> {
  const requestRef = useRef(request);
  requestRef.current = request;
  const [state, setState] = useState<ApiState<T>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    requestRef.current().then(
      (data) => {
        if (active) setState({ status: "success", data });
      },
      (reason: unknown) => {
        if (active) setState({ status: "error", error: reason instanceof Error ? reason : new Error(String(reason)) });
      }
    );
    return () => {
      active = false;
    };
    // The ref always points at the latest request; only explicit caller dependencies trigger refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return state;
}
