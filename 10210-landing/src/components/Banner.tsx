"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";


export function Banner() {
  return (
    <div className="relative top-0 bg-gradient-to-r from-brand-primary to-brand-secondary py-3 text-white md:py-0">
      <div className="container flex flex-col items-center justify-center gap-4 md:h-12 md:flex-row">
        <Link
          href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-up`}
          className="group inline-flex items-center justify-center text-center text-sm leading-loose font-medium"
        >
          <span className="font-bold">
            Turn WhatsApp Group Members Into Leads - Start Converting Today!
          </span>
          <ChevronRight className="ml-1 size-4 transition-all duration-300 ease-out group-hover:translate-x-1" />
        </Link>
      </div>
     
     
    </div>
  );
}