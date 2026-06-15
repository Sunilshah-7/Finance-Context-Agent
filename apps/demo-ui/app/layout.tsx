import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FinContext Agent',
  description: 'Citation-grounded finance context agent prototype'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
