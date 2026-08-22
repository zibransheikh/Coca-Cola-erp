import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  /** "good" (green) / "bad" (destructive) — omit for neutral. Reserve for
   * values with a genuine direction (e.g. profit), not routine counters. */
  tone?: "good" | "bad";
}

export function StatTile({ label, value, hint, tone }: StatTileProps) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 text-2xl font-semibold",
            tone === "good" && "text-emerald-700 dark:text-emerald-400",
            tone === "bad" && "text-destructive"
          )}
        >
          {value}
        </p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
