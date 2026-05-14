"use client";

import { MessageSquarePlus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { env } from "@/env";
import { cn } from "@/lib/utils";

function JialuLogoIcon() {
  return (
    <svg
      aria-label="Jialu AI"
      className="h-6 w-6 object-contain object-left select-none"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient
          id="jialu-logo-gradient"
          x1="15"
          y1="4"
          x2="15"
          y2="26"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="20%" stopColor="#157575" />
          <stop offset="100%" stopColor="#90F4E2" />
        </linearGradient>
      </defs>
      <path
        d="M23 8V26L15 22C15 24.2091 13.2091 26 11 26C8.79086 26 7 24.2091 7 22V17L15 21V4L23 8Z"
        fill="url(#jialu-logo-gradient)"
      />
    </svg>
  );
}

function JialuLogoImage({ collapsed }: { collapsed?: boolean }) {
  if (collapsed) {
    return <JialuLogoIcon />;
  }
  return (
    <div className="ml-1 flex items-center gap-2 select-none">
      <JialuLogoIcon />
      <span className="text-[16px] leading-none font-semibold text-[#02060A] dark:text-[#FAFAFA]">
        Lumax
      </span>
    </div>
  );
}

export function WorkspaceHeader({ className }: { className?: string }) {
  const { t } = useI18n();
  const { state } = useSidebar();
  const pathname = usePathname();
  return (
    <>
      <div
        className={cn(
          "group/workspace-header flex h-12 flex-col justify-center px-1",
          className,
        )}
      >
        {state === "collapsed" ? (
          <div className="group-has-data-[collapsible=icon]/sidebar-wrapper:-translate-y flex w-full cursor-pointer items-center justify-center">
            <div className="block group-hover/workspace-header:hidden">
              <JialuLogoImage collapsed />
            </div>
            <SidebarTrigger className="hidden pl-2 group-hover/workspace-header:block" />
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2">
            {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ? (
              <Link href="/" className="flex items-center">
                <JialuLogoImage />
              </Link>
            ) : (
              <div className="flex cursor-default items-center">
                <JialuLogoImage />
              </div>
            )}
            <SidebarTrigger />
          </div>
        )}
      </div>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname === "/workspace/chats/new"}
            className="h-[40px] rounded-[8px] border border-[#157575] bg-[#157575]! text-white! shadow-[inset_0_0_20px_0_#90F4E2] hover:border-[#157575] hover:bg-[#157575]! hover:text-white! data-[active=true]:bg-[#157575]! data-[active=true]:text-white! dark:border-[#157575] dark:bg-[#157575]! dark:text-white! dark:hover:border-[#157575] dark:hover:bg-[#157575]! dark:hover:text-white! dark:data-[active=true]:bg-[#157575]! dark:data-[active=true]:text-white!"
            asChild
          >
            <Link
              className="flex items-center justify-center gap-2 font-medium"
              href="/workspace/chats/new"
            >
              <MessageSquarePlus size={16} />
              <span>{t.sidebar.newChat}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </>
  );
}
