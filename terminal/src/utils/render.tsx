import { MantineProvider } from "@mantine/core";
import type { RenderOptions } from "@testing-library/react";
import { render as testingRender } from "@testing-library/react";
import type { PropsWithChildren, ReactElement } from "react";
import { theme } from "../theme";
export * from "@testing-library/react";
// Exercise the same theme and provider contracts as the application in jsdom.
export function render(ui: ReactElement, options: RenderOptions = {}) {
  const { wrapper: Wrapper, ...rest } = options;
  return testingRender(ui, {
    ...rest,
    wrapper: ({ children }: PropsWithChildren) => (
      <MantineProvider theme={theme} forceColorScheme="light" env="test">
        {Wrapper ? <Wrapper>{children}</Wrapper> : children}
      </MantineProvider>
    ),
  });
}
