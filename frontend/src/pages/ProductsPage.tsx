import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface Product {
  id: number;
  sku: string;
  name: string;
  unit: string;
  volume_ml: string | null;
  gst_rate: string;
  base_price: string;
  is_returnable: boolean;
  is_active: boolean;
}

const config: ResourceConfig<Product> = {
  title: "Products",
  endpoint: "/products",
  columns: [
    { key: "sku", label: "SKU" },
    { key: "name", label: "Name" },
    { key: "volume_ml", label: "Volume (ml)", render: (row) => row.volume_ml ?? "—" },
    { key: "unit", label: "Unit" },
    { key: "base_price", label: "Price" },
    { key: "gst_rate", label: "GST %" },
  ],
  createFields: [
    { name: "sku", label: "SKU", type: "text", required: true },
    { name: "name", label: "Name", type: "text", required: true },
    { name: "unit", label: "Unit (case, bottle, crate...)", type: "text", required: true },
    { name: "volume_ml", label: "Volume (ml) — used to sort the product list", type: "decimal" },
    { name: "brand", label: "Brand", type: "text" },
    { name: "category", label: "Category", type: "text" },
    { name: "hsn_code", label: "HSN Code", type: "text" },
    { name: "gst_rate", label: "GST Rate %", type: "decimal" },
    { name: "base_price", label: "Base Price", type: "decimal" },
    { name: "deposit_amount", label: "Deposit Amount", type: "decimal" },
    { name: "reorder_level", label: "Reorder Level (0 = no low-stock alert)", type: "decimal" },
    { name: "is_returnable", label: "Returnable (crate/bottle)", type: "boolean" },
  ],
  editFields: [
    { name: "name", label: "Name", type: "text" },
    { name: "unit", label: "Unit", type: "text" },
    { name: "volume_ml", label: "Volume (ml) — used to sort the product list", type: "decimal" },
    { name: "brand", label: "Brand", type: "text" },
    { name: "category", label: "Category", type: "text" },
    { name: "hsn_code", label: "HSN Code", type: "text" },
    { name: "gst_rate", label: "GST Rate %", type: "decimal" },
    { name: "base_price", label: "Base Price", type: "decimal" },
    { name: "deposit_amount", label: "Deposit Amount", type: "decimal" },
    { name: "reorder_level", label: "Reorder Level (0 = no low-stock alert)", type: "decimal" },
    { name: "is_returnable", label: "Returnable (crate/bottle)", type: "boolean" },
    { name: "is_active", label: "Active", type: "boolean" },
  ],
};

export function ProductsPage() {
  return <MasterDataPage config={config} />;
}
