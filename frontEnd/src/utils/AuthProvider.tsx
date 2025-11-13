import { createContext, useEffect, useState, type PropsWithChildren } from "react"
import { onAuthStateChanged, type User } from "firebase/auth";
import { auth } from "../firebase"

type AuthValue = { user: User | null; loading: boolean; getIdToken: () => Promise<string | null>;}

export const AuthContext = createContext<AuthValue>({ 
    user: null as any, 
    loading: true,
    getIdToken: async () => null,
})

export default function AuthProvider({ children }: PropsWithChildren) {
  
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => {
        setUser(u || null);
        setLoading(false);
    })
  }, [])

  async function getIdToken() {
    if (!user) return null;
    try { return await user.getIdToken(false) }
    catch {return null}
  }

  return (
    <AuthContext.Provider value={{ user, loading, getIdToken }}>{children}</AuthContext.Provider>
  )
}

