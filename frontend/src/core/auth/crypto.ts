import CryptoJS from "crypto-js";

const PASSWORD_CRYPTO_KEY = "thanks.platform.";
const PASSWORD_CRYPTO_IV = "thanks.platform.";

function padTo16Bytes(value: string): string {
  const bytes = new TextEncoder().encode(value);
  const result = new Uint8Array(16);
  result.set(bytes.slice(0, 16));
  return new TextDecoder().decode(result);
}

export function encryptPassword(password: string): string {
  const paddedPassword = padTo16Bytes(password);
  const encrypted = CryptoJS.AES.encrypt(
    CryptoJS.enc.Utf8.parse(paddedPassword),
    CryptoJS.enc.Utf8.parse(PASSWORD_CRYPTO_KEY),
    {
      iv: CryptoJS.enc.Utf8.parse(PASSWORD_CRYPTO_IV),
      mode: CryptoJS.mode.CFB,
      padding: CryptoJS.pad.NoPadding,
    },
  );
  return encrypted.ciphertext.toString(CryptoJS.enc.Hex);
}
