/**
 * Static registry of PlantAOx-RAISE components for navigation + the
 * platform overview page. A teammate integrating C1/C3/C4 flips their
 * entry's `status` to "implemented" and adds `routesModule` once their
 * feature directory exports routes -- nothing else here needs to change.
 */

export type ComponentStatus = "implemented" | "not_integrated";

export interface ComponentDescriptor {
  id: string;
  code: "C1" | "C2" | "C3" | "C4";
  title: string;
  shortTitle: string;
  ownerNote: string;
  status: ComponentStatus;
  basePath: string | null;
}

export const COMPONENT_REGISTRY: ComponentDescriptor[] = [
  {
    id: "c1_procon",
    code: "C1",
    title: "AOP-ProCon",
    shortTitle: "C1 : AOP-ProCon",
    ownerNote: "Mechanism-aware representation and prototype analysis",
    status: "implemented",
    basePath: "/c1",
  },
  {
    id: "c2_pu",
    code: "C2",
    title: "PU-AOP",
    shortTitle: "C2 : PU-AOP",
    ownerNote: "Positive-unlabeled antioxidant peptide classification and curriculum learning",
    status: "implemented",
    basePath: "/c2",
  },
  {
    id: "c3_aop_bcs",
    code: "C3",
    title: "AOP-BCS",
    shortTitle: "C3 : AOP-BCS",
    ownerNote: "Predictor behavioral-consistency and reliability auditing",
    status: "implemented",
    basePath: "/c3",
  },
  {
    id: "c4_plantaop_screen",
    code: "C4",
    title: "PlantAOP-Screen",
    shortTitle: "C4 : PlantAOP-Screen",
    ownerNote: "Plant-derived peptide screening and reliability-aware prioritization",
    status: "implemented",
    basePath: "/c4",
  },
];
