import { redirect } from "next/navigation";

export default function MyRubricRedirect() {
  redirect("/settings#priorities");
}
