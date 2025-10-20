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
    <div className="max-w-md rounded-xl border bg-white p-5">
      <h2 className="mb-3 text-xl font-semibold">Sign In</h2>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
        <div>
          <label className="block text-sm font-medium">Full Emory Email</label>
          <input
            {...register("email")}
            placeholder="Avery Student"
            className="mt-1 w-full rounded border px-3 py-2"
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
          <label className="block text-sm font-medium">Password</label>
          <input
            type="password"
            {...register("password")}
            placeholder="••••••••"
            className="mt-1 w-full rounded border px-3 py-2"
            autoComplete="new-password"
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
          className="w-full rounded bg-indigo-600 px-4 py-2 font-semibold text-white disabled:opacity-60"
        >
          {isSubmitting ? "Signing In..." : "Sign In"}
        </button>

        {serverSuccess && (
          <p className="text-sm text-emerald-600 mt-2">{serverSuccess}</p>
        )}
        {serverError && <p className="text-sm text-rose-600 mt-2">{serverError}</p>}
      </form>
    </div>
  )
}


