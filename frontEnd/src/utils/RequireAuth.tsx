
import {useContext, type PropsWithChildren } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { AuthContext } from "./AuthProvider";

export default function RequireAuth({ children }: PropsWithChildren) {
  const { user, loading } = useContext(AuthContext)
  const loc = useLocation();
  
  if (loading) return <div>Checking sign-in...</div>
  if (!user) return <Navigate to="/login" replace state={{ from: loc }} />

  return children
  
}
