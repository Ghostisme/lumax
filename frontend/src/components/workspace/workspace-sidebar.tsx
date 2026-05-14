"use client";

import { useQueryClient } from "@tanstack/react-query";
import { MessageCircle } from "lucide-react";
import Image from "next/image";
import { type FormEvent, useCallback, useEffect, useId, useState } from "react";
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
import { Input } from "@/components/ui/input";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  createEmptyAgentCapabilities,
  createAuthSession,
  DEFAULT_BUSINESS_CODE,
  fetchAvailableAgentPermissions,
  getCaptchaImage,
  getCaptchaStatus,
  loginWithPassword,
  normalizeTenantId,
  pickPrimaryBusinessCode,
  preLoginWithPassword,
  resolveLoginDialogRequest,
  setAuthSession,
  updateAuthSessionAgentPermissions,
  useAuthSession,
  useLoginDialogRequest,
  type LoginTenantOption,
} from "@/core/auth";
import { getFigmaAssetURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";
import { useThreads } from "@/core/threads/hooks";
import { cn } from "@/lib/utils";

import { RecentChatList } from "./recent-chat-list";
import { WorkspaceHeader } from "./workspace-header";
import { WorkspaceNavChatList } from "./workspace-nav-chat-list";
import { WorkspaceNavMenu } from "./workspace-nav-menu";

function EmptyHistoryHint() {
  const { t } = useI18n();
  const { data: threads = [] } = useThreads();

  if (threads.length > 0) {
    return null;
  }

  return (
    <div className="text-muted-foreground/68 flex flex-1 flex-col items-center justify-end pb-4">
      <MessageCircle className="mb-2 size-5 opacity-50" />
      <span className="text-xs">{t.sidebar.noHistory}</span>
    </div>
  );
}

function LoginButton() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const authSession = useAuthSession();
  const loginDialogRequest = useLoginDialogRequest();
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [captchaCode, setCaptchaCode] = useState("");
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [captchaImageUrl, setCaptchaImageUrl] = useState("");
  const [captchaRandomStr, setCaptchaRandomStr] = useState("");
  const [captchaLoading, setCaptchaLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [tenantOptions, setTenantOptions] = useState<
    LoginTenantOption[] | null
  >(null);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [handledLoginRequestId, setHandledLoginRequestId] = useState(0);
  const usernameInputId = useId();
  const passwordInputId = useId();
  const captchaInputId = useId();
  const isLoggedIn = Boolean(authSession?.accessToken);
  const normalizedUsername = username.trim();
  const selectedTenant = tenantOptions?.find(
    (option) => normalizeTenantId(option.tenantId) === selectedTenantId,
  );

  useEffect(() => {
    if (isLoggedIn) {
      setOpen(false);
      setCaptchaRequired(false);
      setCaptchaImageUrl("");
      setCaptchaRandomStr("");
      setCaptchaCode("");
      setTenantOptions(null);
      setSelectedTenantId(null);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (
      loginDialogRequest.id > 0 &&
      loginDialogRequest.id !== handledLoginRequestId &&
      !isLoggedIn &&
      !open
    ) {
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
      setHandledLoginRequestId(loginDialogRequest.id);
      setOpen(true);
    }
  }, [handledLoginRequestId, isLoggedIn, loginDialogRequest.id, open]);

  const resetForm = () => {
    setUsername("");
    setPassword("");
    setCaptchaCode("");
    setCaptchaRequired(false);
    setCaptchaImageUrl("");
    setCaptchaRandomStr("");
    setCaptchaLoading(false);
    setSubmitting(false);
    setTenantOptions(null);
    setSelectedTenantId(null);
  };

  const loadCaptchaImage = useCallback(async (randomStr?: string) => {
    setCaptchaLoading(true);
    try {
      const { randomStr: nextRandomStr, imageDataUrl } =
        await getCaptchaImage(randomStr);
      setCaptchaRandomStr(nextRandomStr);
      setCaptchaImageUrl(imageDataUrl);
      setCaptchaCode("");
    } catch (error) {
      setCaptchaImageUrl("");
      toast.error(error instanceof Error ? error.message : String(error));
    } finally {
      setCaptchaLoading(false);
    }
  }, []);

  const initializeCaptcha = useCallback(async () => {
    setCaptchaLoading(true);
    try {
      const enabled = await getCaptchaStatus();
      setCaptchaRequired(enabled);
      if (enabled) {
        await loadCaptchaImage();
      } else {
        setCaptchaImageUrl("");
        setCaptchaRandomStr("");
        setCaptchaCode("");
      }
    } catch {
      setCaptchaRequired(false);
      setCaptchaImageUrl("");
      setCaptchaRandomStr("");
      setCaptchaCode("");
    } finally {
      setCaptchaLoading(false);
    }
  }, [loadCaptchaImage]);

  const handleOpenChange = (nextOpen: boolean) => {
    if (submitting) {
      return;
    }
    if (nextOpen && isLoggedIn) {
      return;
    }
    setOpen(nextOpen);
    if (!nextOpen) {
      resetForm();
    }
  };

  useEffect(() => {
    if (!open || isLoggedIn) {
      return;
    }
    void initializeCaptcha();
  }, [open, isLoggedIn, initializeCaptcha]);

  const completeLogin = async (tenantId?: string) => {
    const payload = await loginWithPassword({
      username: normalizedUsername,
      password,
      code: captchaRequired ? captchaCode.trim() : undefined,
      randomStr: captchaRequired ? captchaRandomStr : undefined,
      tenantId,
    });
    const tenantForContext =
      tenantOptions?.find(
        (option) => normalizeTenantId(option.tenantId) === tenantId,
      ) ?? null;
    const businessCode = tenantForContext
      ? pickPrimaryBusinessCode(tenantForContext.businessCodes)
      : DEFAULT_BUSINESS_CODE;
    const baseSession = createAuthSession(payload, {
      username: normalizedUsername,
      tenantId,
      businessCode,
    });
    setAuthSession({
      ...baseSession,
      agentPermissionStatus: "loading",
    });
    try {
      const permissionResult = await fetchAvailableAgentPermissions();
      updateAuthSessionAgentPermissions({
        status: "ready",
        capabilities: permissionResult.capabilities,
        availableAgents: permissionResult.items,
      });
    } catch {
      updateAuthSessionAgentPermissions({
        status: "error",
        capabilities: createEmptyAgentCapabilities(),
        availableAgents: [],
      });
    }
    resolveLoginDialogRequest();
    await queryClient.invalidateQueries({ queryKey: ["threads", "search"] });
    toast.success(t.sidebar.loginDialog.success);
    setOpen(false);
    resetForm();
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!normalizedUsername || !password.trim()) {
      toast.error(t.sidebar.loginDialog.validationRequired);
      return;
    }
    if (captchaRequired && !captchaCode.trim()) {
      toast.error(t.sidebar.loginDialog.validationCaptchaRequired);
      return;
    }

    try {
      setSubmitting(true);
      const preLoginInfo = await preLoginWithPassword({
        grantType: "password",
        username: normalizedUsername,
        password,
      });
      const nextTenantOptions = preLoginInfo.tenantOptions ?? [];
      if (nextTenantOptions.length === 0) {
        await completeLogin();
        return;
      }

      setTenantOptions(nextTenantOptions);
      setSelectedTenantId(
        normalizeTenantId(
          nextTenantOptions.find((option) => option.status !== 1)?.tenantId ??
            nextTenantOptions[0]?.tenantId,
        ) ?? null,
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
      if (captchaRequired) {
        void loadCaptchaImage();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmTenantLogin = async () => {
    if (selectedTenantId === null) {
      toast.error(t.sidebar.loginDialog.validationTenantRequired);
      return;
    }
    if (selectedTenant?.status === 1) {
      toast.error(t.sidebar.loginDialog.validationTenantDisabled);
      return;
    }

    try {
      setSubmitting(true);
      await completeLogin(selectedTenantId);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
      if (captchaRequired) {
        void loadCaptchaImage();
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Button
        className="w-full rounded-xl border border-[#157575] bg-[var(--chat-input-surface)] text-[#181D27] hover:bg-[var(--chat-input-surface)] hover:text-[#181D27] disabled:opacity-80 dark:text-[#FAFAFA] dark:hover:text-[#FAFAFA]"
        size="lg"
        onClick={() => {
          if (isLoggedIn) {
            toast.success(t.sidebar.loginDialog.alreadyLoggedIn);
            return;
          }
          handleOpenChange(true);
        }}
      >
        {isLoggedIn ? t.sidebar.loggedIn : t.sidebar.login}
      </Button>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {tenantOptions
                ? t.sidebar.loginDialog.tenantTitle
                : t.sidebar.loginDialog.title}
            </DialogTitle>
            <DialogDescription>
              {tenantOptions
                ? t.sidebar.loginDialog.tenantDescription
                : t.sidebar.loginDialog.description}
            </DialogDescription>
          </DialogHeader>
          {tenantOptions ? (
            <div className="space-y-4">
              <div className="max-h-[320px] space-y-2 overflow-y-auto pr-1">
                {tenantOptions.map((option, index) => {
                  const tenantId = normalizeTenantId(option.tenantId);
                  const selected = tenantId === selectedTenantId;
                  const disabled =
                    option.status === 1 || tenantId === undefined;
                  const label =
                    option.tenantName ??
                    option.tenantCode ??
                    `${t.sidebar.loginDialog.tenantFallbackName} ${index + 1}`;

                  return (
                    <button
                      key={`${tenantId ?? "tenant"}-${option.tenantCode ?? index}`}
                      type="button"
                      disabled={submitting || disabled}
                      className={cn(
                        "flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left text-sm transition-colors",
                        selected
                          ? "border-[#157575] bg-[#157575] text-white"
                          : "bg-background border-[#D5D7DA] hover:border-[#157575]",
                        disabled ? "cursor-not-allowed opacity-45" : "",
                      )}
                      onClick={() => {
                        if (tenantId !== undefined) {
                          setSelectedTenantId(tenantId);
                        }
                      }}
                    >
                      <span className="font-medium">{label}</span>
                      {option.status === 1 ? (
                        <span className="text-xs">
                          {t.sidebar.loginDialog.tenantDisabled}
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  disabled={submitting}
                  onClick={() => {
                    setTenantOptions(null);
                    setSelectedTenantId(null);
                  }}
                >
                  {t.sidebar.loginDialog.back}
                </Button>
                <Button
                  type="button"
                  className="bg-[#157575] text-white hover:bg-[#157575]/90 dark:text-white"
                  disabled={
                    submitting ||
                    selectedTenantId === null ||
                    selectedTenant?.status === 1
                  }
                  onClick={() => void handleConfirmTenantLogin()}
                >
                  {submitting
                    ? t.sidebar.loginDialog.submitting
                    : t.sidebar.loginDialog.confirmLogin}
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium">
                  {t.sidebar.loginDialog.username}
                </p>
                <Input
                  id={usernameInputId}
                  value={username}
                  autoComplete="username"
                  disabled={submitting}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder={t.sidebar.loginDialog.usernamePlaceholder}
                />
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">
                  {t.sidebar.loginDialog.password}
                </p>
                <Input
                  id={passwordInputId}
                  type="password"
                  value={password}
                  autoComplete="current-password"
                  disabled={submitting}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={t.sidebar.loginDialog.passwordPlaceholder}
                />
              </div>
              {captchaRequired ? (
                <div className="space-y-2">
                  <p className="text-sm font-medium">
                    {t.sidebar.loginDialog.captcha}
                  </p>
                  <div className="flex items-center gap-2">
                    <Input
                      id={captchaInputId}
                      value={captchaCode}
                      autoComplete="off"
                      disabled={submitting || captchaLoading}
                      onChange={(event) => setCaptchaCode(event.target.value)}
                      placeholder={t.sidebar.loginDialog.captchaPlaceholder}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      disabled={submitting || captchaLoading}
                      onClick={() => void loadCaptchaImage()}
                    >
                      {t.sidebar.loginDialog.refreshCaptcha}
                    </Button>
                  </div>
                  {captchaImageUrl ? (
                    <img
                      className="h-10 w-[120px] cursor-pointer rounded border object-contain"
                      src={captchaImageUrl}
                      alt={t.sidebar.loginDialog.captchaImageAlt}
                      onClick={() => void loadCaptchaImage()}
                    />
                  ) : (
                    <p className="text-muted-foreground text-xs">
                      {t.sidebar.loginDialog.captchaLoading}
                    </p>
                  )}
                </div>
              ) : null}
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  disabled={submitting}
                  onClick={() => handleOpenChange(false)}
                >
                  {t.common.cancel}
                </Button>
                <Button
                  type="submit"
                  className="bg-[#157575] text-white hover:bg-[#157575]/90 dark:text-white"
                  disabled={submitting}
                >
                  {submitting
                    ? t.sidebar.loginDialog.submitting
                    : t.sidebar.loginDialog.submit}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export function WorkspaceSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const { open: isSidebarOpen } = useSidebar();
  const authSession = useAuthSession();

  useEffect(() => {
    if (
      !authSession?.accessToken ||
      authSession.agentPermissionStatus === "loading" ||
      authSession.agentPermissionStatus === "ready"
    ) {
      return;
    }
    if (authSession.agentPermissionStatus !== "idle") {
      return;
    }
    let cancelled = false;
    updateAuthSessionAgentPermissions({ status: "loading" });
    void fetchAvailableAgentPermissions()
      .then((permissionResult) => {
        if (cancelled) {
          return;
        }
        updateAuthSessionAgentPermissions({
          status: "ready",
          capabilities: permissionResult.capabilities,
          availableAgents: permissionResult.items,
        });
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        updateAuthSessionAgentPermissions({
          status: "error",
          capabilities: createEmptyAgentCapabilities(),
          availableAgents: [],
        });
      });
    return () => {
      cancelled = true;
    };
  }, [authSession?.accessToken, authSession?.agentPermissionStatus]);

  return (
    <>
      <Sidebar
        variant="sidebar"
        collapsible="icon"
        className="workspace-sidebar-shell md:pr-2"
        {...props}
      >
        <SidebarHeader className="py-2.5">
          <WorkspaceHeader />
        </SidebarHeader>
        <SidebarContent className="px-1.5">
          <WorkspaceNavChatList />
          {isSidebarOpen && <RecentChatList />}
          {isSidebarOpen && <EmptyHistoryHint />}
        </SidebarContent>
        <SidebarFooter className="gap-2 border-t border-[var(--chat-sidebar-border)]/68 px-3 py-3">
          {/* legacy-mismatch(sidebar): settings/login blocks do not match Figma bottom profile strip */}
          <div className="hidden">
            <WorkspaceNavMenu />
          </div>
          {isSidebarOpen && <SidebarProfileBar />}
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
    </>
  );
}

function SidebarProfileBar() {
  const { t } = useI18n();
  const authSession = useAuthSession();
  const isLoggedIn = Boolean(authSession?.accessToken);
  const rawUsername = authSession?.username;
  const displayName =
    typeof rawUsername === "string" && rawUsername.trim().length > 0
      ? rawUsername.trim()
      : "用户";
  if (!isLoggedIn) {
    return <LoginButton />;
  }

  return (
    <div className="flex h-[48px] items-center rounded-xl px-1">
      <WorkspaceNavMenu
        trigger={
          <button
            type="button"
            aria-label={t.workspace.settingsAndMore}
            className="flex w-full min-w-0 items-center justify-center gap-2 rounded-lg px-1 py-1 text-center transition hover:bg-[var(--chat-sidebar-item-hover)] focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)] focus-visible:outline-none data-[state=open]:bg-[var(--chat-sidebar-item-active)]"
          >
            <span className="relative h-9 w-9 shrink-0">
              <Image
                src={getFigmaAssetURL("lumax-light/light-avatar.png")}
                alt={displayName}
                fill
                sizes="36px"
                unoptimized
                className="object-contain dark:hidden"
              />
              <Image
                src={getFigmaAssetURL("lumax-dark/dark-avatar.png")}
                alt={displayName}
                fill
                sizes="36px"
                unoptimized
                className="hidden object-contain dark:block"
              />
            </span>
            <span className="max-w-[120px] truncate text-[13px] text-[#666666] dark:text-[#DDDDDD]">
              {displayName}
            </span>
          </button>
        }
      />
    </div>
  );
}
