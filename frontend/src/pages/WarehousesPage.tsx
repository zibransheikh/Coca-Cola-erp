import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface Warehouse {
  id: number;
  name: string;
  address: string | null;
  is_active: boolean;
}

const config: ResourceConfig<Warehouse> = {
  title: "Warehouses",
  endpoint: "/warehouses",
  columns: [
    { key: "name", label: "Name" },
    { key: "address", label: "Address" },
  ],
  createFields: [
    { name: "name", label: "Name", type: "text", required: true },
    { name: "address", label: "Address", type: "text" },
  ],
  editFields: [
    { name: "name", label: "Name", type: "text" },
    { name: "address", label: "Address", type: "text" },
    { name: "is_active", label: "Active", type: "boolean" },
  ],
};

export function WarehousesPage() {
  return <MasterDataPage config={config} />;
}
