"use client";

import Image from "next/image";
import { useSearchParams } from "next/navigation";

import { getFigmaAssetURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

function WelcomeVoiceIcon() {
  return (
    <svg
      aria-hidden="true"
      className="welcome-voice-icon h-auto w-[6.25rem] text-[#157575] select-none sm:w-[7.625rem] 2xl:w-[10rem]"
      viewBox="0 0 122 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M0 9.5C0 9.83333 0 10.1667 0 10.5C2.03333 10.5 4.06667 10.5 6.1 10.5C42.7 10.5 79.3 10.5 115.9 10.5C117.933 10.5 119.967 10.5 122 10.5C122 10.1667 122 9.83333 122 9.5C119.967 9.5 117.933 9.5 115.9 9.5C79.3 9.5 42.7 9.5 6.1 9.5C4.06667 9.5 2.03333 9.5 0 9.5Z"
        fill="currentColor"
      />
      <g className="welcome-voice-bars">
        <path d="M17 19.5V0" stroke="currentColor" />
        <path d="M23 13L23 7" stroke="currentColor" />
        <path d="M11 13L11 7" stroke="currentColor" />
        <path d="M19 17L19 3" stroke="currentColor" />
        <path d="M15 17L15 3" stroke="currentColor" />
        <path d="M21 15L21 5" stroke="currentColor" />
        <path d="M13 15L13 5" stroke="currentColor" />
        <path d="M37 15.1813V4.54492" stroke="currentColor" />
        <path d="M31 11.636L31 8.36328" stroke="currentColor" />
        <path d="M35 13.818L35 6.18164" stroke="currentColor" />
        <path d="M33 12.728L33 7.27344" stroke="currentColor" />
        <path d="M43 12.5913V7.13672" stroke="currentColor" />
        <path d="M39 16L39 4" stroke="currentColor" />
        <path d="M41 13.818L41 6.18164" stroke="currentColor" />
        <path d="M53 18.6355V0.908203" stroke="currentColor" />
        <path d="M47 12.726L47 7.27148" stroke="currentColor" />
        <path d="M51 16.364L51 3.63672" stroke="currentColor" />
        <path d="M49 14.546L49 5.45508" stroke="currentColor" />
        <path d="M59 14.3194V5.22852" stroke="currentColor" />
        <path d="M55 20L55 0" stroke="currentColor" />
        <path d="M57 16.364L57 3.63672" stroke="currentColor" />
        <path d="M98 12.5916V7.27344" stroke="currentColor" />
        <path d="M92 10.818L92 9.18164" stroke="currentColor" />
        <path d="M96 11.91L96 8.0918" stroke="currentColor" />
        <path d="M94 11.364L94 8.63672" stroke="currentColor" />
        <path d="M104 11.2956V8.56836" stroke="currentColor" />
        <path d="M100 13L100 7" stroke="currentColor" />
        <path d="M102 11.91L102 8.0918" stroke="currentColor" />
        <path d="M110 12.5916V7.27344" stroke="currentColor" />
        <path d="M104 10.818L104 9.18164" stroke="currentColor" />
        <path d="M108 11.91L108 8.0918" stroke="currentColor" />
        <path d="M106 11.364L106 8.63672" stroke="currentColor" />
        <path d="M116 11.2956V8.56836" stroke="currentColor" />
        <path d="M112 13L112 7" stroke="currentColor" />
        <path d="M114 11.91L114 8.0918" stroke="currentColor" />
      </g>
    </svg>
  );
}

export function Welcome({
  className,
  mode: _mode,
}: {
  className?: string;
  mode?: "ultra" | "pro" | "thinking" | "flash";
}) {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const greetingRaw = t.welcome.greeting.replaceAll("\n", "").trim();
  const [beforeBrand = "你好，我是", afterBrand = "很高兴为你服务"] =
    greetingRaw.split("Lumax");

  if (searchParams.get("mode") === "skill") {
    return (
      <div
        className={cn(
          "mx-auto flex w-full flex-col items-center justify-center gap-2 px-8 py-4 text-center",
          className,
        )}
      >
        <div className="text-2xl font-bold">
          {`✨ ${t.welcome.createYourOwnSkill} ✨`}
        </div>
        <div className="text-muted-foreground text-sm">
          {t.welcome.createYourOwnSkillDescription.includes("\n") ? (
            <pre className="font-sans whitespace-pre">
              {t.welcome.createYourOwnSkillDescription}
            </pre>
          ) : (
            <p>{t.welcome.createYourOwnSkillDescription}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "relative mx-auto flex w-full flex-col items-start justify-between gap-3 px-3 pt-[3px] pb-[7px] sm:flex-row sm:items-end sm:gap-5 sm:px-2",
        className,
      )}
    >
      <div className="flex -translate-y-[45%] flex-col items-start gap-3 pl-1 sm:pl-2 xl:-translate-y-[70%] 2xl:-translate-y-[80%]">
        <div className="max-w-[378px] text-[1.75rem] leading-[1.5] font-medium tracking-[-0.012em] text-[#fafafa] sm:text-[2.25rem] xl:text-[2.5rem] 2xl:text-[2.75rem]">
          <div className="flex flex-row items-center gap-2">
            <span className="-mb-px block whitespace-nowrap text-[#02060A] dark:text-[#FAFAFA]">
              {beforeBrand.trim()}
            </span>
            <span className="block font-semibold whitespace-nowrap text-[#157575]">
              Lumax
            </span>
          </div>
          <span className="block whitespace-nowrap text-[#02060A] dark:text-[#FAFAFA]">
            {afterBrand.trim()}
          </span>
        </div>
        <WelcomeVoiceIcon />
      </div>

      <div className="relative z-[-1] flex shrink-0 items-end gap-2 self-end sm:self-auto">
        <Image
          src={getFigmaAssetURL("lumax-common/lumaxIPNew.gif")}
          alt="Jialu mascot"
          width={370}
          height={493}
          priority
          unoptimized
          className="relative z-0 h-[clamp(157.6px,24.28vw,932px)] w-auto translate-x-[10%] translate-y-[10%] select-none"
        />
        {/*  shadow-[0_8px_24px_oklch(0_0_0_/_0.3)]*/}
      </div>
    </div>
  );
}
