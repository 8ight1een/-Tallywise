import { useQuery } from '@tanstack/react-query'
import { request } from './api'
import { useAuth } from './auth'
export function useResource<T>(path: string) {
  const { session } = useAuth()
  const userId = session.status === 'user' ? session.user.id : null
  const query = useQuery({
    queryKey: ['user', userId, path],
    queryFn: ({ signal }) => request<T>(path, { signal }),
    enabled: userId !== null,
  })
  return {
    data: query.data,
    error: query.error ?? undefined,
    loading: query.isPending || query.isFetching,
  }
}
