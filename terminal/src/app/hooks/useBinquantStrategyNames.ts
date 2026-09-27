import { useEffect, useState } from "react";

const BINQUANT_TREE_URL =
  "https://api.github.com/repos/carkod/binquant/git/trees/master?recursive=1";
const BINQUANT_RAW_URL =
  "https://raw.githubusercontent.com/carkod/binquant/master";

type GitHubTreeEntry = {
  path: string;
  type: "blob" | "tree";
};

const getStrategyNamesFromFile = async (
  file: GitHubTreeEntry,
  signal: AbortSignal,
): Promise<string[]> => {
  const relativePath = file.path
    .replace(/^strategies\//, "")
    .replace(/\.py$/, "");
  const fileName = relativePath.split("/").at(-1) ?? relativePath;
  const names = new Set([
    fileName.toLowerCase(),
    relativePath.replaceAll("/", "_").toLowerCase(),
  ]);
  const response = await fetch(`${BINQUANT_RAW_URL}/${file.path}`, { signal });

  if (!response.ok) return [...names];

  const source = await response.text();

  for (const match of source.matchAll(/\bALGO\s*=\s*["']([^"']+)["']/g)) {
    names.add(match[1].toLowerCase());
  }

  return [...names];
};

export const fetchBinquantStrategyNames = async (
  signal: AbortSignal,
): Promise<Set<string>> => {
  const response = await fetch(BINQUANT_TREE_URL, {
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error("Unable to load the Binquant strategies directory");
  }

  const { tree } = (await response.json()) as { tree: GitHubTreeEntry[] };
  const strategyFiles = tree.filter(
    ({ path, type }) =>
      type === "blob" && path.startsWith("strategies/") && path.endsWith(".py"),
  );
  const strategyNames = await Promise.all(
    strategyFiles.map((file) => getStrategyNamesFromFile(file, signal)),
  );

  return new Set(strategyNames.flat());
};

let cachedStrategyNames: Set<string> | undefined;

export const useBinquantStrategyNames = () => {
  const [strategyNames, setStrategyNames] = useState<Set<string>>(
    () => cachedStrategyNames ?? new Set(),
  );
  const [isLoading, setIsLoading] = useState(!cachedStrategyNames);
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (cachedStrategyNames) return;

    const controller = new AbortController();

    fetchBinquantStrategyNames(controller.signal)
      .then((names) => {
        cachedStrategyNames = names;
        setStrategyNames(names);
      })
      .catch((requestError: unknown) => {
        if (
          requestError instanceof Error &&
          requestError.name === "AbortError"
        ) {
          return;
        }

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load Binquant strategies",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, []);

  return { strategyNames, isLoading, error };
};
