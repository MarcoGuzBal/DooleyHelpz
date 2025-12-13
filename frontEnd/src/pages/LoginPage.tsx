import { useState } from "react";
import { motion } from "framer-motion";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../utils/api";

import applogo from "../assets/dooleyHelpzAppLogo.png";
import mascot from "../assets/EHMascot.png";

/* ------------------------- Validation (Zod) ------------------------- */
const schema = z.object({
  email: z
    .string()
    .email("Enter a valid email")
    .refine(
      (v) => v.toLowerCase().endsWith("@emory.edu"),
      "Use your @emory.edu email"
    ),
  password: z.string().min(6, "Password must be at least 6 characters"),
});
type FormData = z.infer<typeof schema>;

function mapFirebase(code?: string) {
  switch (code) {
    case "auth/invalid-email":
      return "Please enter a valid email address.";
    case "auth/user-not-found":
      return "You are not yet registered.";
    case "auth/wrong-password":
      return "Email or password is incorrect.";
    case "auth/invalid-credential":
      return "Email or password is incorrect.";
    case "auth/too-many-requests":
      return "Too many attempts. Please wait and try again.";
    default:
      return "Something went wrong. Please try again.";
  }
}

/* ------------------------- Component ------------------------- */
export default function LoginPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormData) {
    setServerError(null);
    try {
      const userCredential = await signInWithEmailAndPassword(auth, values.email, values.password);
      const uid = userCredential.user.uid;
      
      // Register/ensure UID is in database (silently fail if it errors)
      try {
        await api.registerUser(uid, values.email);
      } catch (apiErr) {
        console.error("Failed to register UID in database:", apiErr);
        // Continue to dashboard anyway since auth succeeded
      }
      
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      console.error("Login error:", err);
      const errorCode = err?.code;
      
      // Map Firebase error codes to user-friendly messages
      if (errorCode === "auth/user-not-found") {
        setServerError("You are not yet registered.");
      } else {
        setServerError(mapFirebase(errorCode));
      }
    }
  }

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      {/* Top bar */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
            <img
              src={applogo}
              alt="DooleyHelpz logo"
              className="h-6 w-6 object-contain"
            />
          </div>
          <span className="text-lg font-semibold text-emoryBlue">
            DooleyHelpz
          </span>
        </Link>

        <Link
          to="/register"
          className="hidden rounded-xl bg-lighterBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90 md:inline-block"
        >
          Create account
        </Link>
      </header>

      {/* Main: split layout */}
      <main className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-8 md:grid-cols-2">
        {/* Left: Brand / Pitch */}
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="order-2 md:order-1"
        >
          <div className="relative overflow-hidden rounded-3xl border border-zinc-200 bg-linear-to-br from-emoryBlue/5 via-white to-paleGold/30 p-6">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-emoryBlue md:text-3xl">
                  Welcome back 👋
                </h1>
                <p className="mt-2 max-w-prose text-sm text-zinc-600">
                  Sign in with your{" "}
                  <span className="font-medium">@emory.edu</span> email to get
                  personalized course recommendations and a conflict-free
                  schedule.
                </p>
                <ul className="mt-4 space-y-2 text-sm text-zinc-700">
                  <li>• Smart, degree-aware suggestions</li>
                  <li>• Auto-schedule around classes, work, & life</li>
                  <li>• Clean, distraction-free planning</li>
                </ul>
              </div>
              <img
                src={mascot}
                alt="DooleyHelpz Mascot"
                className="h-28 w-auto -scale-x-100 drop-shadow md:h-36"
              />
            </div>
          </div>
        </motion.section>

        {/* Right: Form Card */}
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
          className="order-1 md:order-2"
        >
          <div className="w-full rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <h2 className="mb-1 text-xl font-semibold text-emoryBlue">
              Sign in
            </h2>
            <p className="mb-4 text-sm text-zinc-600">
              Use your Emory email and password to access your dashboard.
            </p>

            {/* Server error */}
            {serverError && (
              <div
                className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
                role="alert"
              >
                {serverError}
              </div>
            )}

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-3"
              noValidate
            >
              {/* Email */}
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-zinc-800"
                >
                  Full Emory Email
                </label>
                <input
                  id="email"
                  type="email"
                  {...register("email")}
                  placeholder="you@emory.edu"
                  className="mt-1 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-emoryBlue"
                  autoComplete="email"
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? "email-error" : undefined}
                />
                {errors.email && (
                  <p
                    id="email-error"
                    role="alert"
                    className="mt-1 text-sm text-rose-600"
                  >
                    {errors.email.message}
                  </p>
                )}
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-zinc-800"
                >
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  {...register("password")}
                  placeholder="••••••••"
                  className="mt-1 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-emoryBlue"
                  autoComplete="current-password"
                  aria-invalid={!!errors.password}
                  aria-describedby={
                    errors.password ? "password-error" : undefined
                  }
                />
                {errors.password && (
                  <p
                    id="password-error"
                    role="alert"
                    className="mt-1 text-sm text-rose-600"
                  >
                    {errors.password.message}
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="pt-1">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-xl bg-emoryBlue px-4 py-2.5 text-sm font-semibold text-white hover:bg-emoryBlue/90 disabled:opacity-60"
                >
                  {isSubmitting ? "Signing in..." : "Sign in"}
                </button>

                {/* New user CTA */}
                <div className="mt-3 text-center text-sm">
                  <span className="text-zinc-600">New here?</span>{" "}
                  <Link
                    to="/register"
                    className="font-semibold text-emoryBlue hover:text-Gold"
                  >
                    Create an account
                  </Link>
                </div>
              </div>
            </form>

            {/* Secondary links (optional) */}
            <div className="mt-4 text-center text-xs text-zinc-500">
              <Link to="/" className="hover:text-Gold">
                ← Back to home
              </Link>
            </div>
          </div>
        </motion.section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-emoryBlue md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emoryBlue text-white">
              {/* tiny logo box */}
              <img
                src={applogo}
                alt="DooleyHelpz"
                className="h-4 w-4 object-contain"
              />
            </div>
            <span>DooleyHelpz</span>
          </div>
          <div className="text-xs text-zinc-500">
            © {new Date().getFullYear()} DooleyHelpz
          </div>
        </div>
      </footer>
    </div>
  );
}
