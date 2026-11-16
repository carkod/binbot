import { AppShell, Box, LoadingOverlay } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router";
import { Slide, ToastContainer } from "react-toastify";
import { getToken } from "../utils/login";
import Footer from "./components/Footer";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import { MicrostructureProvider } from "./providers/MicrostructureProvider";
import { SpinnerContext } from "./spinner-context";
export const Layout = () => {
  const token = getToken();
  const mobile = useMediaQuery("(max-width: 47.99em)", false, {
    getInitialValueInEffect: false,
  });
  const [mobileOpened, setMobileOpened] = useState(false);
  const [desktopOpened, setDesktopOpened] = useState(true);
  const [spinner, setSpinner] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(
      () => window.dispatchEvent(new Event("resize")),
      300,
    );
    return () => window.clearTimeout(timer);
  }, [mobileOpened, desktopOpened]);
  if (!token) return <Navigate to="/login" replace />;
  return (
    <AppShell
      header={{ height: 64 }}
      navbar={{
        width: 240,
        breakpoint: "md",
        collapsed: { mobile: !mobileOpened, desktop: !desktopOpened },
      }}
      padding={{ base: "sm", md: "lg" }}
      transitionDuration={300}
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
      <AppShell.Header>
        <Header
          expanded={mobile ? mobileOpened : desktopOpened}
          onExpand={() =>
            mobile
              ? setMobileOpened(!mobileOpened)
              : setDesktopOpened(!desktopOpened)
          }
        />
      </AppShell.Header>
      <AppShell.Navbar p="md" className="terminal-sidebar">
        <Sidebar onNavigate={() => setMobileOpened(false)} />
      </AppShell.Navbar>
      <AppShell.Main>
        <Box pos="relative" mih="calc(100dvh - 110px)">
          <LoadingOverlay
            visible={spinner}
            zIndex={200}
            loaderProps={{
              color: "warning",
              "aria-label": "Loading",
              role: "status",
            }}
          />
          <SpinnerContext.Provider value={{ spinner, setSpinner }}>
            <MicrostructureProvider>
              <Outlet />
            </MicrostructureProvider>
          </SpinnerContext.Provider>
        </Box>
        <Footer />
      </AppShell.Main>
    </AppShell>
  );
};
