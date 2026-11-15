import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Planet X | SPHEREx Explorer",
  description: "Explore SPHEREx observations across the sky.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
