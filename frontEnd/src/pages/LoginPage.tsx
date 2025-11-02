import React, { useState } from 'react'
import { signInWithEmailAndPassword, updateProfile} from 'firebase/auth';
import { auth } from '../firebase';
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate } from 'react-router-dom';

// Zod Rules, Come back to this later
const schema = z.object({
  email: z.string()
  .email("Enter a valid email")
  .refine(
    (v) => v.toLowerCase().endsWith("@emory.edu"),"Use your @emory.edu email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type FormData = z.infer<typeof schema>;

function mapFirebase(code?: string) {
  switch (code) {
    case "auth/invalid-email":        return "Please enter a valid email address.";
    case "auth/user-not-found":        return "You are not yet registered";
    case "auth/wrong-password":        return "Email or Password is incorrect";
    case "auth/too-many-requests":    return "Too many attempts. Please wait and try again.";
    default:                          return "Something went wrong. Please try again.";
    }
  }

export default function LoginPage() {
  
  const navigate = useNavigate();
  
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverSuccess, setServerSuccess] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormData) {
    try {
      await signInWithEmailAndPassword(auth, values.email, values.password);
      // Success → Firebase signs in → App listener updates UI
      navigate("/dashboard", { replace: true }); // or back to the page they tried
    } catch (err: any) {
      setServerError(mapFirebase(err?.code));
    }
  }

  return (
    <div className="min-h-screen bg-white text-zinc-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-xl font-semibold text-emoryBlue">Sign In</h2>
  
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
          <div>
            <label className="block text-sm font-medium text-zinc-800">
              Full Emory Email
            </label>
            <input
              type="email"
              {...register("email")}
              placeholder="you@emory.edu"
              className="mt-1 w-full rounded border border-zinc-300 bg-white px-3 py-2 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-emoryBlue"
              autoComplete="email"
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? "email-error" : undefined}
            />
            {errors.email && (
              <p id="email-error" role="alert" className="mt-1 text-sm text-rose-600">
                {errors.email.message}
              </p>
            )}
          </div>
  
          <div>
            <label className="block text-sm font-medium text-zinc-800">
              Password
            </label>
            <input
              type="password"
              {...register("password")}
              placeholder="••••••••"
              className="mt-1 w-full rounded border border-zinc-300 bg-white px-3 py-2 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-emoryBlue"
              autoComplete="current-password"
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? "password-error" : undefined}
            />
            {errors.password && (
              <p id="password-error" role="alert" className="mt-1 text-sm text-rose-600">
                {errors.password.message}
              </p>
            )}
          </div>
  
          <button
            disabled={isSubmitting}
            className="w-full rounded bg-emoryBlue px-4 py-2 font-semibold text-white hover:bg-emoryBlue/90 disabled:opacity-60"
          >
            {isSubmitting ? "Signing In..." : "Sign In"}
          </button>
  
          {serverSuccess && (
            <p className="mt-2 text-sm text-emerald-600">{serverSuccess}</p>
          )}
          {serverError && (
            <p className="mt-2 text-sm text-rose-600">{serverError}</p>
          )}
        </form>
      </div>
    </div>
  );
}


