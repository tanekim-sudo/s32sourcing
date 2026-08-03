import { redirect } from "next/navigation";

/** Settings first — nothing to show until tracking is configured. */
export default function HomePage() {
  redirect("/settings");
}
