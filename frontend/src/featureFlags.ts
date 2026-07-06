function enabled(value: string | boolean | undefined): boolean {
  return value === true || String(value ?? "").toLowerCase() === "true";
}

export const featureFlags = {
  enableAdvancedAttackControls: enabled(import.meta.env.VITE_ENABLE_ADVANCED_ATTACK_CONTROLS),
  enableGoogleAuth: enabled(import.meta.env.VITE_ENABLE_GOOGLE_AUTH),
  enableLegacyPages: enabled(import.meta.env.VITE_ENABLE_LEGACY_PAGES)
};
