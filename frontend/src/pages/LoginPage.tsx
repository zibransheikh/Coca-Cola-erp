import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch {
      setError("Incorrect email or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-svh md:grid-cols-2">
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <p className="font-heading text-2xl font-bold text-primary">DMS</p>
          <h1 className="mt-6 text-2xl font-semibold">Sign in</h1>
          <p className="mt-1 text-sm text-muted-foreground">Distributor Management System</p>

          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={submitting} className="mt-2">
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </div>
      </div>

      <div className="relative hidden overflow-hidden bg-primary md:block">
        <div className="absolute -left-24 -top-32 h-96 w-96 rounded-full bg-white/10" />
        <div className="absolute -bottom-40 -right-16 h-[28rem] w-[28rem] rounded-full bg-white/10" />
        <div className="absolute right-10 top-1/3 h-40 w-40 rounded-full bg-white/10" />

        <div className="relative flex h-full flex-col justify-center px-16">
          <p className="font-heading text-5xl font-bold text-primary-foreground">DMS</p>
          <h2 className="mt-6 max-w-sm text-3xl font-semibold text-primary-foreground">
            Run your distribution business from one place.
          </h2>
          <p className="mt-4 max-w-sm text-primary-foreground/80">
            Inventory, van sales, credit, collections, and accounting — all in sync, all in real time.
          </p>
        </div>
      </div>
    </div>
  );
}
