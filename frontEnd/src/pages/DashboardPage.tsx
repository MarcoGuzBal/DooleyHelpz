import React from 'react'
import { auth } from "../firebase";

function DashboardPage() {
  
  const user = auth.currentUser;
  return (
    <div className="p-6">
      {user ? (
        <h1 className="text-xl font-semibold">
          Hello, {user.email || "there"}!
        </h1>
      ) : (
        <h1 className="text-xl font-semibold">Welcome, guest!</h1>
      )}
    </div>
  )
}

export default DashboardPage
