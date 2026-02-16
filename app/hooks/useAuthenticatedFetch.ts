import { useMemo } from 'react'
import axios, { AxiosInstance } from 'axios'
import { useAuth } from '@/context/AuthContext'

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000'

export function useAuthenticatedFetch(): AxiosInstance {
  const { session } = useAuth()

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add auth token to every request
    instance.interceptors.request.use((config) => {
      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`
      }
      return config
    })

    // Handle 401 errors (token expired)
    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Session is invalid, user will be redirected by AuthProvider
          console.warn('Session expired or invalid')
        }
        return Promise.reject(error)
      }
    )

    return instance
  }, [session?.access_token])

  return api
}