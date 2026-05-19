import { formatStatus } from "../../lib/format";
import type { TargetStatus } from "../../types/target";

const statusClassMap: Record<TargetStatus, string> = {
  completed: "bg-c3mr-success/10 text-c3mr-success",
  in_progress: "bg-c3mr-warning/10 text-c3mr-warning",
  pending: "bg-c3mr-danger/10 text-c3mr-danger",
};

export function StatusBadge({ status }: { status: TargetStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusClassMap[status]}`}>
      {formatStatus(status)}
    </span>
  );
}
