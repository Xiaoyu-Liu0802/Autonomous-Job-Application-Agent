"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/matches", label: "Matches" },
  { href: "/applications", label: "Applications" },
  { href: "/discovery", label: "Discovery" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-8 px-6">
        <Link href="/" className="flex items-center gap-2 py-4 font-semibold">
          <span className="text-lg">🛫</span>
          <span>JobPilot</span>
        </Link>
        <nav className="flex gap-1">
          {LINKS.map((l) => {
            const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
