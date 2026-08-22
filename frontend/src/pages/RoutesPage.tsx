import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface Route {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
}

const config: ResourceConfig<Route> = {
  title: "Routes",
  endpoint: "/routes",
  columns: [
    { key: "name", label: "Name" },
    { key: "description", label: "Description" },
  ],
  createFields: [
    { name: "name", label: "Name", type: "text", required: true },
    { name: "description", label: "Description", type: "text" },
  ],
  editFields: [
    { name: "name", label: "Name", type: "text" },
    { name: "description", label: "Description", type: "text" },
    { name: "is_active", label: "Active", type: "boolean" },
  ],
};

export function RoutesPage() {
  return <MasterDataPage config={config} />;
}
