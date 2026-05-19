export type TargetStatus = "completed" | "in_progress" | "pending";

export interface Target {
  id: string;
  customerName: string;
  address: string;
  phone: string;
  amountDue: number;
  assignedOfficer: string | null;
  officerName?: string | null;
  status: TargetStatus;
}
