export const FULL_SPRITE_PROFILE=Object.freeze({
id:'CONSOLE_FULL',
availability:'SLOT_A_ALL_CARTRIDGES',
birdPath:'console-assets/full-bird-192.webp',
riderPath:'console-assets/rider-attachments.webp',
riderMapPath:'console-assets/rider-attachments.json',
birdOwner:'STRUTHIO CONSOLE MACHINE',
riderOwner:'STRUTHIO CONSOLE MACHINE',
riderStates:32,
riderDefault:false,
verticalAscent:true,
verticalAscentFrames:Object.freeze([186,187,188,189,190,191]),
});
export const DEV00_SPRITE_PROFILE=Object.freeze({
id:'DEV00_SIMPLE',
availability:'DEV-00_INTERNAL_ROM_ONLY',
birdPath:'episodes/dev-00/assets/war-bird-192.webp',
riderPath:'episodes/dev-00/assets/dev00-rider-attachments.webp',
riderMapPath:'episodes/dev-00/assets/dev00-rider-attachments.json',
birdOwner:'DEV-00 INTERNAL ROM',
riderOwner:'DEV-00 INTERNAL ROM',
riderStates:8,
riderDefault:true,
verticalAscent:false,
verticalAscentFrames:Object.freeze([]),
});
export function selectSpriteProfile({source,episodeId}){
if (source==='internal'){
if (episodeId!=='dev-00') throw new Error('SPRITE_PROFILE_DENIED: internal profile is reserved for DEV-00');
return DEV00_SPRITE_PROFILE;
}
return FULL_SPRITE_PROFILE;
}
