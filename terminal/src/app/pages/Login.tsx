import { type FC } from "react";
import { Card } from "react-bootstrap";
import { LoginForm } from "../components/LoginForm";
import { Slide, ToastContainer } from "react-toastify";

export const LoginPage: FC<{}> = () => {
  return (
    <div
      className="d-flex justify-content-center align-items-center"
      style={{ height: "100vh" }}
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
      <Card className="p-4">
        <Card.Body>
          <Card.Title className="p-2">Login</Card.Title>
          <LoginForm />
        </Card.Body>
      </Card>
    </div>
  );
};

export default LoginPage;
