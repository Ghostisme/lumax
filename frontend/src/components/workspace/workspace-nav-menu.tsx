"use client";

import {
  ChevronsUpDown,
  InfoIcon,
  LogOutIcon,
  Settings2Icon,
  SettingsIcon,
} from "lucide-react";
import { type ReactElement, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { clearAuthSession, logoutWithToken, useAuthSession } from "@/core/auth";
import { useI18n } from "@/core/i18n/hooks";

import { SettingsDialog } from "./settings";

function NavMenuButtonContent({
  isSidebarOpen,
  t,
}: {
  isSidebarOpen: boolean;
  t: ReturnType<typeof useI18n>["t"];
}) {
  return isSidebarOpen ? (
    <div className="flex w-full items-center gap-2 text-left text-sm text-[var(--chat-text-soft)]">
      <SettingsIcon className="size-4" />
      <span>{t.workspace.settingsAndMore}</span>
      <ChevronsUpDown className="ml-auto size-4 text-[var(--chat-text-soft)]" />
    </div>
  ) : (
    <div className="flex size-full items-center justify-center">
      <SettingsIcon className="size-4 text-[var(--chat-text-soft)]" />
    </div>
  );
}

export function WorkspaceNavMenu({ trigger }: { trigger?: ReactElement }) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsDefaultSection, setSettingsDefaultSection] = useState<
    "appearance" | "memory" | "tools" | "skills" | "notification" | "about"
  >("appearance");
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false);
  const [logoutSubmitting, setLogoutSubmitting] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { open: isSidebarOpen } = useSidebar();
  const authSession = useAuthSession();
  const { t } = useI18n();
  const isLoggedIn = Boolean(authSession?.accessToken);

  useEffect(() => {
    setMounted(true);
  }, []);

  async function handleConfirmLogout() {
    if (!isLoggedIn) {
      toast.error(t.workspace.notLoggedIn);
      setLogoutConfirmOpen(false);
      return;
    }

    setLogoutSubmitting(true);
    try {
      await logoutWithToken();
      toast.success(t.workspace.logoutSuccess);
    } catch (error) {
      toast.error(
        `${error instanceof Error ? error.message : String(error)}；${t.workspace.logoutRemoteFailedLocalCleared}`,
      );
    } finally {
      clearAuthSession();
      setLogoutSubmitting(false);
      setLogoutConfirmOpen(false);
    }
  }

  const menuContent = (
    <DropdownMenuContent
      className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
      align="end"
      sideOffset={4}
    >
      <DropdownMenuGroup>
        <DropdownMenuItem
          onClick={() => {
            setSettingsDefaultSection("appearance");
            setSettingsOpen(true);
          }}
        >
          <Settings2Icon />
          {t.common.settings}
        </DropdownMenuItem>

        {/* <DropdownMenuSeparator /> */}
        {/* <a
          href="https://deerflow.tech/"
          target="_blank"
          rel="noopener noreferrer"
        >
          <DropdownMenuItem>
            <GlobeIcon />
            {t.workspace.officialWebsite}
          </DropdownMenuItem>
        </a> */}
        {/* <a
          href="https://github.com/bytedance/deer-flow"
          target="_blank"
          rel="noopener noreferrer"
        >
          <DropdownMenuItem>
            <GithubIcon />
            {t.workspace.visitGithub}
          </DropdownMenuItem>
        </a> */}
        {/* <DropdownMenuSeparator /> */}
        {/* <a
          href="https://github.com/bytedance/deer-flow/issues"
          target="_blank"
          rel="noopener noreferrer"
        >
          <DropdownMenuItem>
            <BugIcon />
            {t.workspace.reportIssue}
          </DropdownMenuItem>
        </a> */}
        {/* <a href="mailto:support@deerflow.tech">
          <DropdownMenuItem>
            <MailIcon />
            {t.workspace.contactUs}
          </DropdownMenuItem>
        </a> */}
      </DropdownMenuGroup>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        onClick={() => {
          setSettingsDefaultSection("about");
          setSettingsOpen(true);
        }}
      >
        <InfoIcon />
        {t.workspace.about}
      </DropdownMenuItem>
      <DropdownMenuItem
        onClick={() => {
          setLogoutConfirmOpen(true);
        }}
      >
        <LogOutIcon />
        {t.workspace.logout}
      </DropdownMenuItem>
    </DropdownMenuContent>
  );

  const dropdownMenu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {trigger ?? (
          <SidebarMenuButton
            size="lg"
            className="h-10 rounded-xl border border-[var(--chat-sidebar-border)]/70 bg-transparent hover:bg-[var(--chat-sidebar-item-hover)] data-[state=open]:bg-[var(--chat-sidebar-item-active)] data-[state=open]:text-[var(--chat-text-title)]"
          >
            <NavMenuButtonContent isSidebarOpen={isSidebarOpen} t={t} />
          </SidebarMenuButton>
        )}
      </DropdownMenuTrigger>
      {menuContent}
    </DropdownMenu>
  );

  return (
    <>
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        defaultSection={settingsDefaultSection}
      />
      {trigger ? (
        mounted ? dropdownMenu : trigger
      ) : (
        <SidebarMenu className="w-full">
          <SidebarMenuItem>
            {mounted ? (
              dropdownMenu
            ) : (
              <SidebarMenuButton size="lg" className="pointer-events-none">
                <NavMenuButtonContent isSidebarOpen={isSidebarOpen} t={t} />
              </SidebarMenuButton>
            )}
          </SidebarMenuItem>
        </SidebarMenu>
      )}
      <Dialog open={logoutConfirmOpen} onOpenChange={setLogoutConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.workspace.logoutConfirmTitle}</DialogTitle>
            <DialogDescription>
              {t.workspace.logoutConfirmDescription}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={logoutSubmitting}
              onClick={() => setLogoutConfirmOpen(false)}
            >
              {t.common.cancel}
            </Button>
            <Button
              variant="destructive"
              disabled={logoutSubmitting}
              onClick={() => void handleConfirmLogout()}
            >
              {logoutSubmitting
                ? t.workspace.logoutSubmitting
                : t.workspace.logout}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
