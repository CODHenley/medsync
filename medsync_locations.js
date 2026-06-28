// medsync_locations.js — single source of truth for Scout Vet location IDs
// Include this before any page script that uses LOC_IDS, LOC_NAMES, VID_MAP, etc.

const LOCS = [
  { key: 'lp', uuid: '11111111-0000-0000-0000-000000000001', vid: '23083', name: 'Lincoln Park',  region: 'Chicagoland' },
  { key: 'oo', uuid: '11111111-0000-0000-0000-000000000002', vid: '27390', name: 'Old Orchard',   region: 'Chicagoland' },
  { key: 'wl', uuid: '11111111-0000-0000-0000-000000000003', vid: '24356', name: 'West Loop',     region: 'Chicagoland' },
  { key: 'wh', uuid: '11111111-0000-0000-0000-000000000004', vid: '28253', name: 'Wheaton',       region: 'Chicagoland West' },
];

const LOC_IDS   = Object.fromEntries(LOCS.map(l => [l.key,  l.uuid]));
const LOC_NAMES = Object.fromEntries(LOCS.map(l => [l.uuid, l.name]));
const LOC_UUID  = Object.fromEntries(LOCS.map(l => [l.vid,  l.uuid]));
const VID_MAP   = Object.fromEntries(LOCS.map(l => [l.name, l.vid]));
const ALL_LOC_UUIDS = LOCS.map(l => l.uuid);

const WHEATON_UUID = LOCS[3].uuid;
const WHEATON_VID  = LOCS[3].vid;

// Coming soon — lease signed, not yet live
const COMING_SOON_LOCS = [
  { key: 'wc', uuid: '11111111-0000-0000-0000-000000000005', name: 'Westchester', region: 'Chicagoland West', liveDate: null },
];
