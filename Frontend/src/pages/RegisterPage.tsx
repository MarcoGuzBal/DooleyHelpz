import React, { useState } from 'react'
import { createUserWithEmailAndPassword, updateProfile} from 'firebase/auth';
import { auth } from '../firebase';
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";


// Delcaring Validation Schema
// Below is what the valid input will look like:
const schema = z
  .object({
    email: z
      .string()
      .email("Enter a valid email")
      .refine(
        (v) => v.toLowerCase().endsWith("@emory.edu"),
        "Use your @emory.edu email"
      ),
    password: z.string().min(6, "Password must be at least 6 characters"),
    confirm: z.string().min(6, "Confirm your password")
  })
  .refine((data) => data.password === data.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

// Typescript form of the schema
type FormData =  z.infer<typeof schema>;

// Maps errors codes based to friendly messages
// The error codes are from Firebase
function mapFirebase(code?: string) {
    switch (code) {
      case "auth/email-already-in-use": return "That email is already registered.";
      case "auth/invalid-email":        return "Please enter a valid email address.";
      case "auth/weak-password":        return "Password must be at least 6 characters.";
      case "auth/too-many-requests":    return "Too many attempts. Please wait and try again.";
      default:                          return "Something went wrong. Please try again.";
    }
  }

export default function RegisterRHFZod() {
  
  // React-hook-form is setup with the schema we setup earlier
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", confirm: ""},
  });

  // States for server error/success messages
  const [serverError, setServerError] = React.useState<string | null>(null);
  const [serverSuccess, setServerSuccess] = React.useState<string | null>(null);

  // The function that is called when the Submit Button is clicked
  async function onSubmit(values: FormData) {
    setServerError(null)
    setServerSuccess(null);
    
    // Testing to make sure the values are correct
    //console.log("Email:", values.email);
    //console.log("Password:", values.password);

    try {
      // The email, password is sent to Firebase so that the account is created
      const cred = await createUserWithEmailAndPassword(auth, values.email, values.password);
      setServerSuccess("Account created! You're signed in.") // Success Message 
      reset({ email:values.email, password: "", confirm: ""}); // Clears the Fields
    } catch (err: any){
      // Sets the Server Error to the code we are given. 
      setServerError(mapFirebase(err?.code));
    }
  }

  return (
    <div className="max-w-md rounded-xl border bg-white p-5">
      <h2 className="mb-3 text-xl font-semibold">Create your account</h2>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>

        <div>
          <label className="block text-sm font-medium">Emory email</label>
          <input
            type="email"
            {...register("email")}
            placeholder="you@emory.edu"
            className="mt-1 w-full rounded border px-3 py-2"
            inputMode="email"
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

        <div>
          <label className="block text-sm font-medium">Confirm password</label>
          <input
            type="password"
            {...register("confirm")}
            placeholder="••••••••"
            className="mt-1 w-full rounded border px-3 py-2"
            autoComplete="new-password"
            aria-invalid={!!errors.confirm}
            aria-describedby={errors.confirm ? "confirm-error" : undefined}
          />
          {errors.confirm && (
            <p id="confirm-error" role="alert" className="mt-1 text-sm text-rose-600">
              {errors.confirm.message}
            </p>
          )}
        </div>

        <button
          disabled={isSubmitting}
          className="w-full rounded bg-indigo-600 px-4 py-2 font-semibold text-white disabled:opacity-60"
        >
          {isSubmitting ? "Creating..." : "Create account"}
        </button>

        {serverSuccess && (
          <p className="text-sm text-emerald-600 mt-2">{serverSuccess}</p>
        )}
        {serverError && <p className="text-sm text-rose-600 mt-2">{serverError}</p>}
      </form>
    </div>
  );
}


