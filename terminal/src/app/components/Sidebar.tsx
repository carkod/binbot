import {
  Anchor,
  Group,
  NavLink,
  ScrollArea,
  Stack,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { Link, matchPath, useLocation } from "react-router";
import { routes } from "../routes";
export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  return (
    <Stack h="100%" gap="lg">
      <Anchor
        component={Link}
        to="/"
        onClick={onNavigate}
        underline="never"
        c="primary.5"
      >
        <Group gap="sm">
          <ThemeIcon size="lg" variant="light">
            <i className="fa-solid fa-wave-square" />
          </ThemeIcon>
          <Title order={2} size="h3">
            Binbot
          </Title>
        </Group>
      </Anchor>
      <ScrollArea flex={1}>
        <Stack gap={4}>
          {routes
            .filter((route) => route.nav)
            .map((route) => (
              <NavLink
                key={route.link ?? route.path}
                component={Link}
                to={route.link}
                label={route.name}
                active={
                  route.index
                    ? pathname === "/"
                    : Boolean(
                        matchPath(
                          { path: route.link ?? route.path, end: false },
                          pathname,
                        ),
                      )
                }
                leftSection={
                  route.icon ? (
                    <i className={route.icon} aria-hidden="true" />
                  ) : undefined
                }
                pl={route.icon ? "sm" : "xl"}
                onClick={onNavigate}
              />
            ))}
        </Stack>
      </ScrollArea>
    </Stack>
  );
}
