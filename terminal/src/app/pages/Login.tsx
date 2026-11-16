import { Box, Card, Title } from "@mantine/core";
import { type FC } from "react";
import { Slide, ToastContainer } from "react-toastify";
import { LoginForm } from "../components/LoginForm";
export const LoginPage: FC<{}> = () => {
  return (
    <Box
      display="flex"
      style={{
        ...{ height: "100vh" },
        justifyContent: "center",
        alignItems: "center",
      }}
      component="div"
    >
      <ToastContainer
        transition={Slide}
        position="top-right"
        autoClose={5000}
        hideProgressBar
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss={false}
        draggable={false}
        pauseOnHover
        theme="colored"
      />
      <Card mb="md" p={24}>
        <Box>
          <Title order={4} p={8}>
            Login
          </Title>
          <LoginForm />
        </Box>
      </Card>
    </Box>
  );
};
export default LoginPage;
