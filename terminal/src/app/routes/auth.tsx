import type { LoaderFunctionArgs } from "react-router";
import { redirect } from "react-router";
import { getToken } from "../../utils/login";

export function protectedLoader({ request }: LoaderFunctionArgs) {
  const token = getToken();

  if (token) {
    let params = new URLSearchParams();
    params.set("from", new URL(request.url).pathname);
    return redirect("/login?" + params.toString());
  }
  return null;
}
