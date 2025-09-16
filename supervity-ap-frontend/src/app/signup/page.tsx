"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { signup } from "@/lib/api";
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

export default function SignupPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    try {
      await signup({ email, password });

      // Show different messages based on email domain
      if (email.endsWith("@supervity.ai")) {
        toast.success(
          "Registration successful! Your account has been activated and you can log in immediately.",
        );
      } else {
        toast.success(
          "Registration successful! Please wait for an administrator to approve your account.",
        );
      }

      router.push("/login");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Signup failed");
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
          <CardTitle className="pt-4">Create an Account</CardTitle>
          <CardDescription>Sign up to get started</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="Email"
              required
            />
            <Input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder="Password"
              required
            />
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sign Up
            </Button>
            <p className="text-center text-sm">
              Already have an account?{" "}
              <a
                href="/login"
                className="text-blue-primary font-semibold hover:underline"
              >
                Log in
              </a>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
