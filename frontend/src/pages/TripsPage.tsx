import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { listResource } from "@/lib/masterData";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Trip {
  id: number;
  vehicle_id: number;
  driver_id: number;
  route_id: number | null;
  warehouse_id: number;
  trip_date: string;
  status: string;
}

interface NamedRef {
  id: number;
  name: string;
}
interface VehicleRef {
  id: number;
  registration_number: string;
}
interface EmployeeRef {
  id: number;
  name: string;
}

// Trips only have two meaningful states in the UI: open (still editable) or
// closed — no separate loading/on_route/returned stages. Explicit semantic
// colors rather than the brand-red "default" badge variant, since red here
// would read as a warning on a perfectly normal open trip.
const OPEN_CLASS = "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300";
const CLOSED_CLASS = "bg-secondary text-secondary-foreground";

export function TripsPage() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [vehicles, setVehicles] = useState<VehicleRef[]>([]);
  const [drivers, setDrivers] = useState<EmployeeRef[]>([]);
  const [routes, setRoutes] = useState<NamedRef[]>([]);
  const [warehouses, setWarehouses] = useState<NamedRef[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ vehicle_id: "", driver_id: "", route_id: "", warehouse_id: "", trip_date: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");

  async function refresh() {
    const data = await listResource<Trip>("/trips");
    setTrips(data);
  }

  useEffect(() => {
    refresh();
    listResource<VehicleRef>("/vehicles").then(setVehicles);
    listResource<EmployeeRef>("/employees").then(setDrivers);
    listResource<NamedRef>("/routes").then(setRoutes);
    listResource<NamedRef>("/warehouses").then(setWarehouses);
  }, []);

  function openDialog() {
    setForm({ vehicle_id: "", driver_id: "", route_id: "", warehouse_id: "", trip_date: "" });
    setError(null);
    setDialogOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { data } = await api.post("/trips", {
        vehicle_id: Number(form.vehicle_id),
        driver_id: Number(form.driver_id),
        route_id: form.route_id ? Number(form.route_id) : null,
        warehouse_id: Number(form.warehouse_id),
        trip_date: form.trip_date,
      });
      setDialogOpen(false);
      navigate(`/trips/${data.id}`);
    } catch {
      setError("Could not create trip. Check the values and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const filteredTrips = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return trips;
    return trips.filter((trip) => {
      const vehicle = vehicles.find((v) => v.id === trip.vehicle_id)?.registration_number ?? "";
      const driver = drivers.find((d) => d.id === trip.driver_id)?.name ?? "";
      const route = routes.find((r) => r.id === trip.route_id)?.name ?? "";
      const status = trip.status === "closed" ? "closed" : "open";
      return [trip.trip_date, vehicle, driver, route, status].some((v) => v.toLowerCase().includes(term));
    });
  }, [trips, vehicles, drivers, routes, search]);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Trips</h2>
        <Button onClick={openDialog}>New Trip</Button>
      </div>

      <Input
        placeholder="Search by date, vehicle, driver, route, or status..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 max-w-sm"
      />

      <div className="overflow-x-auto rounded-lg border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Vehicle</TableHead>
              <TableHead>Driver</TableHead>
              <TableHead>Route</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredTrips.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {trips.length === 0 ? "No trips yet." : "No trips match your search."}
                </TableCell>
              </TableRow>
            )}
            {filteredTrips.map((trip) => (
              <TableRow key={trip.id}>
                <TableCell>{trip.trip_date}</TableCell>
                <TableCell>{vehicles.find((v) => v.id === trip.vehicle_id)?.registration_number ?? "—"}</TableCell>
                <TableCell>{drivers.find((d) => d.id === trip.driver_id)?.name ?? "—"}</TableCell>
                <TableCell>{routes.find((r) => r.id === trip.route_id)?.name ?? "—"}</TableCell>
                <TableCell>
                  <Badge className={trip.status === "closed" ? CLOSED_CLASS : OPEN_CLASS}>
                    {trip.status === "closed" ? "Closed" : "Open"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="outline" size="sm" onClick={() => navigate(`/trips/${trip.id}`)}>
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Trip</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Vehicle</Label>
              <Select value={form.vehicle_id} onValueChange={(v) => setForm((f) => ({ ...f, vehicle_id: v }))}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select vehicle" />
                </SelectTrigger>
                <SelectContent>
                  {vehicles.map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      {v.registration_number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Driver</Label>
              <Select value={form.driver_id} onValueChange={(v) => setForm((f) => ({ ...f, driver_id: v }))}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select driver" />
                </SelectTrigger>
                <SelectContent>
                  {drivers.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Route</Label>
              <Select value={form.route_id} onValueChange={(v) => setForm((f) => ({ ...f, route_id: v }))}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select route" />
                </SelectTrigger>
                <SelectContent>
                  {routes.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Warehouse (load-out origin)</Label>
              <Select value={form.warehouse_id} onValueChange={(v) => setForm((f) => ({ ...f, warehouse_id: v }))}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>
                      {w.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="trip_date">Trip Date</Label>
              <Input
                id="trip_date"
                type="date"
                required
                value={form.trip_date}
                onChange={(e) => setForm((f) => ({ ...f, trip_date: e.target.value }))}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating..." : "Create Trip"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
