"use client";

import { MessagesSquare } from "lucide-react";
// import { BotIcon, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";

const sidebarContentItemClass =
  "h-[38px] rounded-[8px] border border-transparent bg-transparent! text-[14px] text-[#666666]! hover:border-transparent hover:bg-transparent! hover:text-[#666666]! active:bg-transparent! active:text-[#666666]! data-[active=true]:border-transparent! data-[active=true]:bg-[#1575751A]! data-[active=true]:text-[#157575]! data-[active=true]:shadow-none! dark:text-[#BBBBBB]! dark:hover:border-transparent dark:hover:bg-transparent! dark:hover:text-[#BBBBBB]! dark:active:bg-transparent! dark:active:text-[#BBBBBB]! dark:data-[active=true]:border-transparent! dark:data-[active=true]:bg-[#1575751A]! dark:data-[active=true]:text-[#157575]!";

export function WorkspaceNavChatList() {
  const { t } = useI18n();
  const pathname = usePathname();
  return (
    <SidebarGroup className="pt-1.5">
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname === "/workspace/chats"}
            className={sidebarContentItemClass}
            asChild
          >
            <Link href="/workspace/chats">
              <MessagesSquare size={16} />
              <span>{t.sidebar.chats}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        {/*
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/agents")}
            className={sidebarContentItemClass}
            asChild
          >
            <Link href="/workspace/agents">
              <BotIcon size={16} />
              <span>{t.sidebar.agents}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        */}
      </SidebarMenu>
    </SidebarGroup>
  );
}
