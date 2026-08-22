import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { createResource, listResource, updateResource, type ResourceConfig } from "@/lib/masterData";

interface EntityBase {
  id: number;
  is_active?: boolean;
}

export function MasterDataPage<T extends EntityBase>({ config }: { config: ResourceConfig<T> }) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<T | null>(null);
  const [search, setSearch] = useState("");

  const filteredItems = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return items;
    return items.filter((item) =>
      config.columns.some((col) => String(item[col.key] ?? "").toLowerCase().includes(term))
    );
  }, [items, search, config.columns]);

  async function refresh() {
    setLoading(true);
    try {
      const data = await listResource<T>(config.endpoint);
      setItems(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.endpoint]);

  function openCreate() {
    setEditingItem(null);
    setDialogOpen(true);
  }

  function openEdit(item: T) {
    setEditingItem(item);
    setDialogOpen(true);
  }

  async function handleSubmit(values: Record<string, unknown>) {
    if (editingItem) {
      await updateResource(config.endpoint, editingItem.id, values);
    } else {
      await createResource(config.endpoint, values);
    }
    await refresh();
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">{config.title}</h2>
        <Button onClick={openCreate}>Add {config.title.replace(/s$/, "")}</Button>
      </div>

      <Input
        placeholder={`Search ${config.title.toLowerCase()}...`}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 max-w-sm"
      />

      <div className="overflow-x-auto rounded-lg border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              {config.columns.map((col) => (
                <TableHead key={col.key}>{col.label}</TableHead>
              ))}
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {!loading && filteredItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={config.columns.length + 2} className="text-center text-muted-foreground">
                  {items.length === 0 ? "No records yet." : "No records match your search."}
                </TableCell>
              </TableRow>
            )}
            {filteredItems.map((item) => (
              <TableRow key={item.id}>
                {config.columns.map((col) => (
                  <TableCell key={col.key}>
                    {col.render ? col.render(item) : String(item[col.key] ?? "")}
                  </TableCell>
                ))}
                <TableCell>
                  {item.is_active === false ? (
                    <Badge variant="secondary">Inactive</Badge>
                  ) : (
                    <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                      Active
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="outline" size="sm" onClick={() => openEdit(item)}>
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <EntityFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title={editingItem ? `Edit ${config.title.replace(/s$/, "")}` : `Add ${config.title.replace(/s$/, "")}`}
        fields={editingItem ? config.editFields : config.createFields}
        initialValues={editingItem ? (editingItem as Record<string, unknown>) : undefined}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
