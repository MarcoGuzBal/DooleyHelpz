// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_KEY,
  authDomain: "dooleyhelpz.firebaseapp.com",
  projectId: "dooleyhelpz",
  storageBucket: "dooleyhelpz.firebasestorage.app",
  messagingSenderId: "1016848634885",
  appId: "1:1016848634885:web:4d5a525831c1051e96f86c"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);