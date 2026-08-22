import { MasterDataPage } from "@/components/MasterDataPage";
import type { ResourceConfig } from "@/lib/masterData";

interface Employee {
  id: number;
  name: string;
  role: string;
  phone: string | null;
  joining_date: string;
  monthly_salary: string;
  is_active: boolean;
}

const roleOptions = [
  { value: "driver", label: "Driver" },
  { value: "helper", label: "Helper" },
  { value: "office", label: "Office" },
  { value: "other", label: "Other" },
];

const config: ResourceConfig<Employee> = {
  title: "Employees",
  endpoint: "/employees",
  columns: [
    { key: "name", label: "Name" },
    { key: "role", label: "Role" },
    { key: "phone", label: "Phone" },
    { key: "joining_date", label: "Joined" },
    { key: "monthly_salary", label: "Salary" },
  ],
  createFields: [
    { name: "name", label: "Name", type: "text", required: true },
    { name: "role", label: "Role", type: "select", options: roleOptions, required: true },
    { name: "phone", label: "Phone", type: "text" },
    { name: "joining_date", label: "Joining Date", type: "date", required: true },
    { name: "monthly_salary", label: "Monthly Salary", type: "decimal" },
  ],
  editFields: [
    { name: "name", label: "Name", type: "text" },
    { name: "role", label: "Role", type: "select", options: roleOptions },
    { name: "phone", label: "Phone", type: "text" },
    { name: "monthly_salary", label: "Monthly Salary", type: "decimal" },
    { name: "is_active", label: "Active", type: "boolean" },
  ],
};

export function EmployeesPage() {
  return <MasterDataPage config={config} />;
}
