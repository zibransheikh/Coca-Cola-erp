import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface ExpenseCategory {
  id: number;
  name: string;
  category_group: string;
}

const groupOptions = [
  { value: "vehicle", label: "Vehicle" },
  { value: "business", label: "Business" },
];

const config: ResourceConfig<ExpenseCategory> = {
  title: "Expense Categories",
  endpoint: "/expense-categories",
  columns: [
    { key: "name", label: "Name" },
    { key: "category_group", label: "Group" },
  ],
  createFields: [
    { name: "name", label: "Name", type: "text", required: true },
    { name: "category_group", label: "Group", type: "select", options: groupOptions, required: true },
  ],
  editFields: [
    { name: "name", label: "Name", type: "text" },
    { name: "category_group", label: "Group", type: "select", options: groupOptions },
  ],
};

export function ExpenseCategoriesPage() {
  return <MasterDataPage config={config} />;
}
