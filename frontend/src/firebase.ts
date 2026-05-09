import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

type RuntimeEnv = Partial<Record<string, string>>;

declare global {
  interface Window {
    __TRACELINK_ENV__?: RuntimeEnv;
  }
}

const runtimeEnv = typeof window === "undefined" ? {} : window.__TRACELINK_ENV__ ?? {};
const env = (key: string) => runtimeEnv[key] || import.meta.env[key];

const firebaseConfig = {
  apiKey: env("VITE_FIREBASE_API_KEY"),
  authDomain: env("VITE_FIREBASE_AUTH_DOMAIN"),
  projectId: env("VITE_FIREBASE_PROJECT_ID"),
  storageBucket: env("VITE_FIREBASE_STORAGE_BUCKET"),
  messagingSenderId: env("VITE_FIREBASE_MESSAGING_SENDER_ID"),
  appId: env("VITE_FIREBASE_APP_ID"),
  measurementId: env("VITE_FIREBASE_MEASUREMENT_ID"),
};

const missingConfig = Object.entries(firebaseConfig)
  .filter(([, value]) => !value)
  .map(([key]) => key);

if (missingConfig.length > 0) {
  throw new Error(`Missing Firebase config: ${missingConfig.join(", ")}`);
}

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export default app;
