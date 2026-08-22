import { useEffect, useState } from "react";
import { MasterDataPage } from "@/components/MasterDataPage";
import { listResource, type ResourceConfig } from "@/lib/masterData";

interface Customer {
  id: number;
  name: string;
  owner_name: string | null;
  phone: string | null;
  route_id: number | null;
  credit_limit: string;
  credit_days: number;
  is_active: boolean;
}

interface Route {
  id: number;
  name: string;
}

export function CustomersPage() {
  const [routes, setRoutes] = useState<Route[]>([]);

  useEffect(() => {
    listResource<Route>("/routes").then(setRoutes);
  }, []);

  const routeOptions = routes.map((r) => ({ value: r.id, label: r.name }));

  const config: ResourceConfig<Customer> = {
    title: "Customers",
    endpoint: "/customers",
    columns: [
      { key: "name", label: "Shop Name" },
      { key: "owner_name", label: "Owner" },
      { key: "phone", label: "Phone" },
      {
        key: "route_id",
        label: "Route",
        render: (row) => routes.find((r) => r.id === row.route_id)?.name ?? "—",
      },
      { key: "credit_limit", label: "Credit Limit" },
    ],
    createFields: [
      { name: "name", label: "Shop Name", type: "text", required: true },
      { name: "owner_name", label: "Owner Name", type: "text" },
      { name: "phone", label: "Phone", type: "text" },
      { name: "address", label: "Address", type: "text" },
      { name: "gst_number", label: "GST Number", type: "text" },
      { name: "route_id", label: "Route", type: "select", options: routeOptions },
      { name: "credit_limit", label: "Credit Limit", type: "decimal" },
      { name: "credit_days", label: "Credit Days", type: "number" },
    ],
    editFields: [
      { name: "name", label: "Shop Name", type: "text" },
      { name: "owner_name", label: "Owner Name", type: "text" },
      { name: "phone", label: "Phone", type: "text" },
      { name: "address", label: "Address", type: "text" },
      { name: "gst_number", label: "GST Number", type: "text" },
      { name: "route_id", label: "Route", type: "select", options: routeOptions },
      { name: "credit_limit", label: "Credit Limit", type: "decimal" },
      { name: "credit_days", label: "Credit Days", type: "number" },
      { name: "is_active", label: "Active", type: "boolean" },
    ],
  };

  return <MasterDataPage config={config} />;
}
