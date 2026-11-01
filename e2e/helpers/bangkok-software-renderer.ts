// Linux CI always takes this path. The flag lets a developer reproduce it
// with the same full Chromium build on a machine that also has a hardware GPU.
export const labUsesSwiftShader = (!!process.env.CI && process.platform === 'linux') ||
  process.env.E2E_SWIFTSHADER === '1';
