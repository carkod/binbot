import { ActionIcon, Burger, Group, Title } from "@mantine/core";
import { Link, matchPath, useLocation } from "react-router";
import { routes } from "../routes";

export const Header = ({
  onExpand,
  expanded = false,
}: {
  onExpand: () => void;
  expanded?: boolean;
}) => {
  const location = useLocation();

  const route = routes.find((route) =>
    route.index
      ? location.pathname === "/"
      : route.path && matchPath(route.path, location.pathname),
  );

  return (
    <Group h="100%" px="lg" justify="space-between" wrap="nowrap">
      <Group wrap="nowrap">
        <Burger
          opened={expanded}
          onClick={onExpand}
          size="sm"
          aria-label="Toggle navigation"
        />
        <Title order={1} size="h4">
          <i className={route?.icon} aria-hidden="true" /> {route?.name}
        </Title>
      </Group>
      <ActionIcon
        component={Link}
        to="/logout"
        variant="subtle"
        color="secondary"
        aria-label="Log out"
      >
        <i className="fa-solid fa-right-from-bracket" aria-hidden="true" />
      </ActionIcon>
    </Group>
  );
};

export default Header;
