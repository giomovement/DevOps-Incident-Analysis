import type { Metadata } from 'next';
import './globals.css';
import './extras.css';
import './protected.css';

export const metadata: Metadata = {
  title: 'DevOps Incident Analysis Suite',
  description: 'Turn operational logs into evidence-backed incidents, approved response actions, and reusable cookbooks.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="antialiased">{children}</body>
    </html>
  );
}
