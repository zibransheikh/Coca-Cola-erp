import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface ChartOfAccount {
  id: number;
  code: string;
  name: string;
  account_type: string;
}

const typeOptions = [
  { value: "asset", label: "Asset" },
  { value: "liability", label: "Liability" },
  { value: "equity", label: "Equity" },
  { value: "income", label: "Income" },
  { value: "expense", label: "Expense" },
];

const config: ResourceConfig<ChartOfAccount> = {
  title: "Chart of Accounts",
  endpoint: "/chart-of-accounts",
  columns: [
    { key: "code", label: "Code" },
    { key: "name", label: "Name" },
    { key: "account_type", label: "Type" },
  ],
  createFields: [
    { name: "code", label: "Code", type: "text", required: true },
    { name: "name", label: "Name", type: "text", required: true },
    { name: "account_type", label: "Type", type: "select", options: typeOptions, required: true },
  ],
  editFields: [{ name: "name", label: "Name", type: "text" }],
};

export function ChartOfAccountsPage() {
  return <MasterDataPage config={config} />;
}
