import React from "react";
import { Navigate, useLocation } from "react-router-dom";

type Props = {
  isAuthed: boolean; // true if a Firebase user is signed in
  children: React.ReactNode; // the protected page to render
};

export default function ProtectedRoute({ isAuthed, children }: Props) {
  const location = useLocation();
  if (!isAuthed) {
    // send to /login and remember where they wanted to go
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
