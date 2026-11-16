import { Text } from "@mantine/core";
export const Footer = () => (
  <Text component="footer" size="xs" c="dimmed" ta="right" mt="xl" py="md">
    &copy; {`2018 - ${new Date().getFullYear()} Binbot`}
  </Text>
);
export default Footer;
