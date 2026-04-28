import { TriState } from '@/components/TriStateToggle';

export type StageAData = {
  occurred_at: string;
  address: string;
  quick_summary: string;
  owner_name: string;
  owner_phone: string;
  owner_insurer: string;
  owner_policy_number: string;
  owner_vin: string;
  owner_plate_number: string;
  other_name: string;
  other_phone: string;
  other_insurer: string;
  other_policy_number: string;
  other_vin: string;
  other_plate_number: string;
  injuries_reported: TriState;
  police_called: TriState;
  drivable: TriState;
  tow_requested: TriState;
};

export const EMPTY_STAGE_A: StageAData = {
  occurred_at: '',
  address: '',
  quick_summary: '',
  owner_name: '',
  owner_phone: '',
  owner_insurer: '',
  owner_policy_number: '',
  owner_vin: '',
  owner_plate_number: '',
  other_name: '',
  other_phone: '',
  other_insurer: '',
  other_policy_number: '',
  other_vin: '',
  other_plate_number: '',
  injuries_reported: 'unknown',
  police_called: 'unknown',
  drivable: 'unknown',
  tow_requested: 'unknown',
};

export type StageBData = {
  detailed_narrative: string;
  damage_summary: string;
  weather_conditions: string;
  road_conditions: string;
  police_report_number: string;
  adjuster_name: string;
  repair_shop_name: string;
  follow_up_notes: string;
};

export const EMPTY_STAGE_B: StageBData = {
  detailed_narrative: '',
  damage_summary: '',
  weather_conditions: '',
  road_conditions: '',
  police_report_number: '',
  adjuster_name: '',
  repair_shop_name: '',
  follow_up_notes: '',
};
