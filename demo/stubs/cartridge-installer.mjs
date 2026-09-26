// STRUTHIO · ARCADE demo edition: this feature is not part of the demo.
export const CARTRIDGE_CACHE='struthio-cartridge-packs-v1';
export async function readInstalledEpisode(){return null;}
export async function ensureCartridgeRouting(){return false;}
export async function installCartridgeZip(){throw new Error('CARTRIDGES_NOT_IN_DEMO');}
export function setupCartridgeManager(){return null;}
