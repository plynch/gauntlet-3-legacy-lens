/// <reference types="vite/client" />

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_SOURCE_REPO_BASE_URL?: string
}
