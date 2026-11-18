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

const navigationRoutes = routes.filter((route) => route.nav);

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();

  const activeRoute = [...navigationRoutes]
    .sort((a, b) => (b.link ?? "").length - (a.link ?? "").length)
    .find((route) =>
      route.index
        ? pathname === "/"
        : matchPath({ path: route.link ?? route.path, end: false }, pathname),
    );

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
          <ThemeIcon size="lg" variant="transparent" c="primary.1">
            <i className="fa-solid fa-wave-square" />
          </ThemeIcon>
          <Title order={2} size="h3">
            Binbot
          </Title>
        </Group>
      </Anchor>
      <ScrollArea flex={1}>
        <Stack gap={4}>
          {navigationRoutes.map((route) => (
            <NavLink
              key={route.link ?? route.path}
              component={Link}
              to={route.link}
              label={route.name}
              active={route === activeRoute}
              aria-current={route === activeRoute ? "page" : undefined}
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
