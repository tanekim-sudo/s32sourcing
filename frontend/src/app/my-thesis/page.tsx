import { redirect } from "next/navigation";

export default function MyThesisRedirect() {
  redirect("/settings#areas");
}
