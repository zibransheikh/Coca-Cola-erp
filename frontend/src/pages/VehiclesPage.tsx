import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface Vehicle {
  id: number;
  registration_number: string;
  vehicle_type: string | null;
  capacity: string | null;
  is_active: boolean;
}

const config: ResourceConfig<Vehicle> = {
  title: "Vehicles",
  endpoint: "/vehicles",
  columns: [
    { key: "registration_number", label: "Registration No." },
    { key: "vehicle_type", label: "Type" },
    { key: "capacity", label: "Capacity" },
  ],
  createFields: [
    { name: "registration_number", label: "Registration Number", type: "text", required: true },
    { name: "vehicle_type", label: "Type", type: "text" },
    { name: "capacity", label: "Capacity", type: "decimal" },
  ],
  editFields: [
    { name: "vehicle_type", label: "Type", type: "text" },
    { name: "capacity", label: "Capacity", type: "decimal" },
    { name: "is_active", label: "Active", type: "boolean" },
  ],
};

export function VehiclesPage() {
  return <MasterDataPage config={config} />;
}
