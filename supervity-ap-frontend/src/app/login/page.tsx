"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { useAppContext } from "@/lib/AppContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import toast from "react-hot-toast";
import { Loader2 } from "lucide-react";
import Image from "next/image";

export default function LoginPage() {
  const router = useRouter();
  const { login: loginContext } = useAppContext();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    const formData = new FormData(event.currentTarget);
    try {
      const data = await login(formData);
      loginContext(data.access_token);
      toast.success("Login successful!");
      router.push("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-bg flex items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <Image
            src="/logo-dark.svg"
            alt="Supervity Logo"
            width={150}
            height={40}
            className="mx-auto"
          />
          <p className="text-sm font-semibold text-gray-600 -mt-2">
            Proactive Loan Command Center
          </p>
          <CardTitle className="pt-4">Welcome Back</CardTitle>
          <CardDescription>
            Enter your credentials to access your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              name="username"
              type="email"
              placeholder="Email (admin@supervity.ai)"
              required
            />
            <Input
              name="password"
              type="password"
              placeholder="Password (SupervityAdmin123!)"
              required
            />
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Log In
            </Button>
            <p className="text-center text-sm">
              No account?{" "}
              <a
                href="/signup"
                className="text-blue-primary font-semibold hover:underline"
              >
                Sign up
              </a>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
