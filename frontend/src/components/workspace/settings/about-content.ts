export interface PersonalCenterAboutInfo {
  companyName: string;
  slogan: string;
  paragraphs: string[];
}

export const personalCenterAgreementUrl =
  "https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud201712130944_39600.html";

export const personalCenterAboutInfo: PersonalCenterAboutInfo = {
  companyName: "嘉鹿集团",
  slogan: "JIALU GROUP",
  paragraphs: [
    "嘉鹿集团成立于2015年，是一家深耕汽车行业的数字营销企业，",
    "总部位于上海，在杭州、苏州、安徽、重庆、广州、北京等多地设立分公司和服务网络，",
    "我们以「算法、内容、数据」构建新营销体系，为汽车品牌提供规模化、可衡量的确定性增长。",
    "行业内的独角兽：全链路品效合一的整合营销服务机构",
    "来客业务行业资质：抖音生活服务四星级直营服务商",
    "10年汽车行业深耕，拥有巨量引擎全链路牌照，融合内容创意与数字化创新，构建品牌效合一的整合营销服务体系，全域覆盖、全链赋能、全程增长",
  ],
};

export const aboutMarkdown = `# ${personalCenterAboutInfo.companyName}

## ${personalCenterAboutInfo.slogan}

${personalCenterAboutInfo.paragraphs.join("\n\n")}

---

<!-- [用户协议](${personalCenterAgreementUrl}) -->
`;
