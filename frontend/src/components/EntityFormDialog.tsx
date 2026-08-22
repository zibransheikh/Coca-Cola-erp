import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { FieldConfig } from "@/lib/masterData";

interface EntityFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  fields: FieldConfig[];
  initialValues?: Record<string, unknown>;
  onSubmit: (values: Record<string, unknown>) => Promise<void>;
}

export function EntityFormDialog({
  open,
  onOpenChange,
  title,
  fields,
  initialValues,
  onSubmit,
}: EntityFormDialogProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setValues(initialValues ?? {});
      setError(null);
    }
  }, [open, initialValues]);

  function setField(name: string, value: unknown) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(values);
      onOpenChange(false);
    } catch {
      setError("Something went wrong. Check the values and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {fields.map((field) => {
            const value = values[field.name];
            if (field.type === "boolean") {
              return (
                <div key={field.name} className="flex items-center justify-between">
                  <Label htmlFor={field.name}>{field.label}</Label>
                  <Switch
                    id={field.name}
                    checked={Boolean(value)}
                    onCheckedChange={(checked) => setField(field.name, checked)}
                  />
                </div>
              );
            }
            if (field.type === "select") {
              return (
                <div key={field.name} className="flex flex-col gap-2">
                  <Label htmlFor={field.name}>{field.label}</Label>
                  <Select
                    value={value !== undefined && value !== null ? String(value) : undefined}
                    onValueChange={(v) => setField(field.name, v)}
                  >
                    <SelectTrigger id={field.name} className="w-full">
                      <SelectValue placeholder={`Select ${field.label.toLowerCase()}`} />
                    </SelectTrigger>
                    <SelectContent>
                      {field.options?.map((opt) => (
                        <SelectItem key={opt.value} value={String(opt.value)}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              );
            }
            return (
              <div key={field.name} className="flex flex-col gap-2">
                <Label htmlFor={field.name}>{field.label}</Label>
                <Input
                  id={field.name}
                  type={field.type === "number" || field.type === "decimal" ? "number" : field.type === "date" ? "date" : "text"}
                  step={field.type === "decimal" ? "0.01" : undefined}
                  required={field.required}
                  value={(value as string | number | undefined) ?? ""}
                  onChange={(e) => setField(field.name, e.target.value)}
                />
              </div>
            );
          })}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
