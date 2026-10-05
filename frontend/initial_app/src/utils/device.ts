export function deviceIdForSetup(setupId: string): string | undefined {
  const setupNumber = setupId.match(/\d+/)?.[0]
  return setupNumber ? `solar_simulator_${setupNumber}` : undefined
}
